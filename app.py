from flask import Flask, render_template, request, redirect, session,send_from_directory, url_for
import sqlite3, os
import pandas as pd
import csv
from flask import flash


app = Flask(__name__)
app.secret_key = "secret123"

# ================= DB CONNECTION =================
def get_db_connection():
    conn = sqlite3.connect("database.db", timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ================= LOG SYSTEM =================
def log_activity(conn, user_id, action, details):
    conn.execute("""
        INSERT INTO activity_logs (user_id, action, details)
        VALUES (?, ?, ?)
    """, (user_id, action, details))

# ================= AUTH DECORATORS =================
def admin_required(f):
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect("/")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def faculty_required(f):
    def wrapper(*args, **kwargs):
        if session.get("role") != "faculty":
            return redirect("/")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def invigilator_required(f):
    def wrapper(*args, **kwargs):
        if session.get("role") != "invigilator":
            return redirect("/")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ================= LOGIN =================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin_dashboard")
            elif user["role"] == "faculty":
                return redirect("/faculty_dashboard")
            else:
                return redirect("/invigilator_dashboard")

    return render_template("login.html")

# ================= ADMIN DASHBOARD =================
@app.route("/admin_dashboard")
@admin_required
def admin_dashboard():

    conn = get_db_connection()

    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_courses = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    total_exams = conn.execute("SELECT COUNT(*) FROM exams").fetchone()[0]
    total_answers = conn.execute("SELECT COUNT(*) FROM student_answers").fetchone()[0]
    evaluated = conn.execute("SELECT COUNT(*) FROM evaluation").fetchone()[0]
    pending = total_answers - evaluated

    assignments = conn.execute("""
        SELECT ea.*, c.course_name, e.exam_name, u.username
        FROM exam_assignments ea
        JOIN courses c ON ea.course_id = c.id
        JOIN exams e ON ea.exam_id = e.id
        LEFT JOIN users u ON ea.assigned_faculty = u.id
    """).fetchall()
    logs = conn.execute("""
        SELECT activity_logs.*, users.username
        FROM activity_logs
        JOIN users ON activity_logs.user_id = users.id
        ORDER BY timestamp DESC
        LIMIT 10
        """).fetchall()

    conn.close()

    return render_template("admin/admin_dashboard.html",
        total_students=total_students,
        total_courses=total_courses,
        total_exams=total_exams,
        total_answers=total_answers,
        evaluated=evaluated,
        pending=pending,
        assignments=assignments,
        logs=logs
        

    )

# ================= FACULTY DASHBOARD =================

@app.route("/faculty_dashboard")
def faculty_dashboard():

    if session.get("role") != "faculty":
        return redirect("/")

    assignment_id = request.args.get("assignment_id")

    conn = get_db_connection()

    # ✅ GET ALL ASSIGNMENTS (ALWAYS REQUIRED FOR DROPDOWN)
    assignments = conn.execute("""
        SELECT ea.id, ea.year, ea.department,
               c.course_name, e.exam_name
        FROM exam_assignments ea
        JOIN courses c ON ea.course_id = c.id
        JOIN exams e ON ea.exam_id = e.id
        WHERE ea.assigned_faculty = ?
    """, (session.get("user_id"),)).fetchall()

    if assignment_id:
        # ✅ FILTERED DATA

        total = conn.execute(
            "SELECT COUNT(*) FROM student_answers WHERE assignment_id=?",
            (assignment_id,)
        ).fetchone()[0]

        evaluated = conn.execute("""
            SELECT COUNT(*)
            FROM evaluation ev
            JOIN student_answers sa
            ON ev.student_answer_id = sa.id
            WHERE sa.assignment_id=? AND ev.evaluator_id=?
        """, (assignment_id, session.get("user_id"))).fetchone()[0]

    else:
        # ✅ ALL DATA

        total = conn.execute(
            "SELECT COUNT(*) FROM student_answers"
        ).fetchone()[0]

        evaluated = conn.execute(
            "SELECT COUNT(*) FROM evaluation WHERE evaluator_id=?",
            (session.get("user_id"),)
        ).fetchone()[0]

    pending = total - evaluated

    conn.close()

    return render_template(
        "faculty/faculty_dashboard.html",
        total=total,
        evaluated=evaluated,
        pending=pending,
        assignments=assignments,   # ✅ IMPORTANT
        assignment_id=assignment_id
    )
# ================= INVIGILATOR DASHBOARD =================

@app.route("/invigilator_dashboard")
@invigilator_required
def invigilator_dashboard():

    conn = get_db_connection()

    answers = conn.execute("""
    SELECT 
        student_answers.id,
        students.roll_no,
        students.student_name,
        courses.course_code,
        exams.exam_name,
        student_answers.file_path
    FROM student_answers
    JOIN students ON student_answers.student_id = students.id
    JOIN courses ON student_answers.course_id = courses.id
    JOIN exams ON student_answers.exam_id = exams.id
    """).fetchall()

    conn.close()

    return render_template(
        "invigilator/invigilator_dashboard.html",
        answers=answers
    ) 
#=================viwe usres ==================

@app.route("/view_users")
@admin_required
def view_users():


    conn = get_db_connection()

    users = conn.execute("SELECT * FROM users").fetchall()

    conn.close()

    return render_template("admin/view_users.html", users=users)

#================= view students ================

@app.route("/view_students", methods=["GET", "POST"])
def view_students():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT department FROM departments")
    departments = cursor.fetchall()

    students = []

    if request.method == "POST":

        department = request.form.get("department")
        year = request.form.get("year")

        if year == "all":

            cursor.execute("""
            SELECT * FROM students
            WHERE department=?
            ORDER BY year, roll_no
            """, (department,))

        else:

            cursor.execute("""
            SELECT * FROM students
            WHERE department=? AND year=?
            ORDER BY roll_no
            """, (department, year))

        students = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/view_students.html",
        departments=departments,
        students=students
    )
#===================  edit student ================

@app.route("/edit_student/<int:id>", methods=["GET","POST"])
@admin_required
def edit_student(id):

    conn = get_db_connection()

    if request.method == "POST":

        
        name = request.form["student_name"]
        dept = request.form["department"]
        year = request.form["year"]

        conn.execute("""
        UPDATE students
        SET student_name=?, department=?, year=?
        WHERE id=?
        """, (name, dept, year, id))

        log_activity(conn, session["user_id"], "Edit Student", f"{name} -> {dept} -> {year}")

        flash("Exam created successfully!", "success")

        conn.commit()
        conn.close()

        return redirect("/view_students")

    student = conn.execute(
        "SELECT * FROM students WHERE id=?", (id,)
    ).fetchone()

    conn.close()

    return render_template("admin/edit_student.html", student=student)

#====================== delete student ============================

@app.route("/delete_student/<int:id>")
@admin_required
def delete_student(id):

    conn = get_db_connection()

    conn.execute("DELETE FROM students WHERE id=?", (id,))

    log_activity(conn, session["user_id"], "Delete Student", f"ID {id}")

    conn.commit()
    conn.close()

    return redirect("/view_students")

#================= view exams ===================

@app.route("/view_exams")
@admin_required
def view_exams():

    conn = get_db_connection()

    exams = conn.execute(
        "SELECT * FROM exams"
    ).fetchall()

    conn.close()

    return render_template(
        "admin/view_exams.html",
        exams=exams
    )

#============== view course ===========

@app.route("/view_courses")
@admin_required
def view_subjects():

    conn = get_db_connection()

    courses = conn.execute("SELECT * FROM courses").fetchall()

    conn.close()

    return render_template("admin/view_courses.html", courses=courses)

# ================= CREATE EXAM =================

@app.route("/create_exam", methods=["GET","POST"])
@admin_required
def create_exam():

    conn = get_db_connection()

    departments = conn.execute("SELECT DISTINCT department FROM students").fetchall()
    courses = conn.execute("SELECT * FROM courses").fetchall()
    exams = conn.execute("SELECT * FROM exams").fetchall()

    if request.method == "POST":

        department = request.form["department"]
        year = request.form["year"]
        course_id = request.form["course"]
        exam_id = request.form["exam"]

        conn.execute("""
        INSERT INTO exam_assignments (department, year, course_id, exam_id)
        VALUES (?, ?, ?, ?)
        """, (department, year, course_id, exam_id))
        

        log_activity(conn, session["user_id"], "Create Exam",
                     f"{department} Year {year}")
        
        

        conn.commit()
        conn.close()
        
        return redirect("/admin_dashboard")

    conn.close()
    return render_template("admin/create_exam.html",
                           departments=departments,
                           courses=courses,
                           exams=exams)

# ================= DELETE EXAM =================

@app.route("/delete_exam/<int:id>")
@admin_required
def delete_exam(id):

    conn = get_db_connection()

    conn.execute("DELETE FROM exam_assignments WHERE id=?", (id,))

    log_activity(conn, session["user_id"], "Delete Exam", f"ID {id}")

    conn.commit()
    conn.close()

    return redirect("/admin_dashboard")

# ================= ASSIGN FACULTY =================

@app.route("/assign_faculty/<int:id>", methods=["GET","POST"])
@admin_required
def assign_faculty(id):

    conn = get_db_connection()

    # Get faculty users
    faculty = conn.execute("""
    SELECT * FROM users WHERE role='faculty'
    """).fetchall()

    if request.method == "POST":

        faculty_id = request.form["faculty"]

        conn.execute("""
        UPDATE exam_assignments
        SET assigned_faculty=?, status='assigned'
        WHERE id=?
        """, (faculty_id, id))

        log_activity(conn, session["user_id"],
                 "Assign Faculty",
                 f"Faculty {faculty_id} → Assignment {id}")


        conn.commit()

        return redirect("/admin_dashboard")

    conn.close()

    return render_template(
        "admin/assign_faculty.html",
        faculty=faculty,
        assignment_id=id
    )

#======================= faculty taske ===========================

@app.route("/faculty_tasks")
@faculty_required
def faculty_tasks():

    conn = get_db_connection()

    tasks = conn.execute("""
    SELECT ea.*, c.course_name, e.exam_name
    FROM exam_assignments ea
    JOIN courses c ON ea.course_id = c.id
    JOIN exams e ON ea.exam_id = e.id
    WHERE ea.assigned_faculty = ?
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template("faculty/tasks.html", tasks=tasks)

#========================= invigilator exam =================================

@app.route("/invigilator_exams")
@invigilator_required
def invigilator_exams():

    conn = get_db_connection()

    exams = conn.execute("""
    SELECT ea.*, c.course_name, e.exam_name
    FROM exam_assignments ea
    JOIN courses c ON ea.course_id = c.id
    JOIN exams e ON ea.exam_id = e.id
    """).fetchall()

    conn.close()

    return render_template("invigilator/exams.html", exams=exams)

# ================= UPLOAD QUESTION =================
@app.route("/upload_question", methods=["GET", "POST"])
@invigilator_required
def upload_question():

    conn = get_db_connection()

    assignment_id = request.args.get("assignment_id")

    if request.method == "POST":

        assignment_id = request.form["assignment_id"]
        file = request.files["file"]

        folder = "uploads/question_papers"
        os.makedirs(folder, exist_ok=True)

        path = os.path.join(folder, file.filename)
        file.save(path)

        conn.execute("""
        INSERT INTO question_papers (file_path, assignment_id)
        VALUES (?, ?)
        """, (path, assignment_id))

        log_activity(conn, session["user_id"],
                     "Upload Question", f"Assignment {assignment_id}")

        conn.commit()
        conn.close()

        return redirect("/invigilator_dashboard")

    conn.close()

    return render_template(
        "invigilator/upload_question.html",
        assignment_id=assignment_id
    )
# ================= UPLOAD MODEL ANSWER =================

@app.route("/upload_model_answer", methods=["GET", "POST"])
@invigilator_required
def upload_model_answer():

    conn = get_db_connection()

    assignment_id = request.args.get("assignment_id")

    if request.method == "POST":

        assignment_id = request.form["assignment_id"]
        file = request.files["file"]

        folder = "uploads/model_answers"
        os.makedirs(folder, exist_ok=True)

        path = os.path.join(folder, file.filename)
        file.save(path)

        conn.execute("""
        INSERT INTO model_answers (file_path, assignment_id)
        VALUES (?, ?)
        """, (path, assignment_id))

        log_activity(conn, session["user_id"],
                     "Upload Model Answer", f"Assignment {assignment_id}")

        conn.commit()
        conn.close()

        return redirect("/invigilator_dashboard")

    conn.close()

    return render_template(
        "invigilator/upload_model_answer.html",
        assignment_id=assignment_id
    )
# ================= UPLOAD STUDENT ANSWERS =================

@app.route("/upload_answer", methods=["GET", "POST"])
@invigilator_required
def upload_answer():

    conn = get_db_connection()

    assignment_id = request.args.get("assignment_id")

    students = conn.execute("SELECT * FROM students").fetchall()

    if request.method == "POST":
        exam_id = request.files["exam_id"]
        course_id = request.form["course_id"]
        assignment_id = request.form["assignment_id"]
        student_id = request.form["student_id"]
        file = request.files["file"]

        folder = "uploads/student_answers"
        os.makedirs(folder, exist_ok=True)

        path = os.path.join(folder, file.filename)
        file.save(path)

        conn.execute("""
        (student_id, course_id, exam_id, file_path, assignment_id)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id,course_id,exam_id, path, assignment_id))

        log_activity(conn, session["user_id"],
                     "Upload Answer",
                     f"Student {student_id} Assignment {assignment_id}")

        conn.commit()
        conn.close()

        return redirect("/invigilator_dashboard")

    conn.close()

    return render_template(
        "invigilator/upload_answer.html",
        assignment_id=assignment_id,
        students=students
    )
#=============== manage exam ===========

@app.route("/manage_exam/<int:id>")
@invigilator_required
def manage_exam(id):

    return render_template("invigilator/manage_exam.html", id=id)

#=============== manage uploads =======

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)


#=============== result ===============================

@app.route("/results_dashboard")
@admin_required
def results_dashboard():

    conn = get_db_connection()

    results = conn.execute("""
    SELECT
    students.roll_no,
    students.student_name,
    courses.course_code,
    exams.exam_name,
    evaluation.marks
    FROM evaluation
    JOIN student_answers ON evaluation.student_answer_id = student_answers.id
    JOIN students ON student_answers.student_id = students.id
    JOIN courses ON student_answers.course_id = courses.id
    JOIN exams ON student_answers.exam_id = exams.id
    """).fetchall()

    conn.close()

    return render_template("admin/results_dashboard.html", results=results)


# ================= VIEW ANSWERS =================

@app.route("/view_student_answers")
@faculty_required
def view_answers():

    assignment_id = request.args.get("assignment_id")

    conn = get_db_connection()

    answers = conn.execute("""
    SELECT sa.id, s.roll_no, s.student_name,
           sa.file_path, ev.marks
    FROM student_answers sa
    JOIN students s ON sa.student_id = s.id
    LEFT JOIN evaluation ev
    ON sa.id = ev.student_answer_id
    WHERE sa.assignment_id=?
    """, (assignment_id,)).fetchall()

    conn.close()

    return render_template("faculty/view_student_answers.html",
                           answers=answers,
                           assignment_id=assignment_id)

# ================= EVALUATE =================

@app.route("/evaluate/<int:answer_id>", methods=["GET", "POST"])
@faculty_required
def evaluate(answer_id):

    conn = get_db_connection()

    # Get answer (for assignment_id redirect)
    answer = conn.execute("""
    SELECT * FROM student_answers WHERE id=?
    """, (answer_id,)).fetchone()

    if request.method == "POST":

        marks = request.form["marks"]
        comments = request.form["comments"]

        # 🔥 PREVENT DUPLICATE ENTRY
        existing = conn.execute("""
        SELECT * FROM evaluation WHERE student_answer_id=?
        """, (answer_id,)).fetchone()

        if existing:
            conn.execute("""
            UPDATE evaluation
            SET marks=?, comments=?, evaluator_id=?
            WHERE student_answer_id=?
            """, (marks, comments, session["user_id"], answer_id))
        else:
            conn.execute("""
            INSERT INTO evaluation (student_answer_id, marks, comments, evaluator_id)
            VALUES (?, ?, ?, ?)
            """, (answer_id, marks, comments, session["user_id"]))
            
            log_activity(conn, session["user_id"],
                 "Evaluate Answer",
                 f"Answer ID {id}, Marks {marks}")


        conn.commit()
        conn.close()

        # ✅ Redirect back properly
        return redirect(f"/view_student_answers?assignment_id={answer['assignment_id']}")

    data = conn.execute("""
    SELECT sa.file_path, s.student_name
    FROM student_answers sa
    JOIN students s ON sa.student_id = s.id
    WHERE sa.id=?
    """, (answer_id,)).fetchone()

    conn.close()

    return render_template(
        "faculty/evaluate.html",
        data=data
    )

#===============bulk upload =============

@app.route("/bulk_upload_students", methods=["POST"])
@admin_required
def bulk_upload_students():

    file = request.files["file"]

    conn = get_db_connection()

    reader = csv.reader(file.stream.read().decode("UTF-8").splitlines())

    for row in reader:
        conn.execute("""
        INSERT INTO students (roll_no, student_name, department, year)
        VALUES (?, ?, ?, ?)
        """, row)

    log_activity(conn, session["user_id"], "Bulk Upload", "Students CSV")

    conn.commit()
    conn.close()

    return redirect("/view_students")


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)