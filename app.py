from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import sqlite3
from config import Config
import os
from functools import wraps
from flask import session, redirect, url_for
import pandas as pd
from flask import flash

app = Flask(__name__)
app.config.from_object(Config)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if 'role' not in session or session['role'] != 'admin':
            return redirect(url_for('login'))

        return f(*args, **kwargs)

    return decorated_function


def faculty_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if 'role' not in session or session['role'] != 'faculty':
            return redirect(url_for('login'))

        return f(*args, **kwargs)

    return decorated_function


def invigilator_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if 'role' not in session or session['role'] != 'invigilator':
            return redirect(url_for('login'))

        return f(*args, **kwargs)

    return decorated_function


def get_db_connection():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/", methods=["GET","POST"])
def home():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username,password)
        ).fetchone()

        conn.close()

        if user:
            session["user_id"] = user["id"]   # ✅ IMPORTANT
            session["user"] = user["username"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin_dashboard")

            if user["role"] == "faculty":
                return redirect("/faculty_dashboard")

            if user["role"] == "invigilator":
                return redirect("/invigilator_dashboard")

        else:
            return "Invalid Credentials"

    return render_template("login.html")


@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():

    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # statistics queries
    cursor.execute("SELECT COUNT(*) as total_students FROM students")
    total_students = cursor.fetchone()["total_students"]

    cursor.execute("SELECT COUNT(*) as total_courses FROM courses")
    total_courses = cursor.fetchone()["total_courses"]

    cursor.execute("SELECT COUNT(*) as total_exams FROM exams")
    total_exams = cursor.fetchone()["total_exams"]

     # ----------------------------
    # NEW: EXAM ASSIGNMENTS
    # ----------------------------
    cursor.execute("""
    SELECT ea.*, c.course_name, e.exam_name, u.username
    FROM exam_assignments ea
    JOIN courses c ON ea.course_id = c.id
    JOIN exams e ON ea.exam_id = e.id
    LEFT JOIN users u ON ea.assigned_faculty = u.id
    """)
    assignments = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/admin_dashboard.html",
        total_students=total_students,
        total_courses=total_courses,
        total_exams=total_exams,
        assignments=assignments
        
    )

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


@app.route("/invigilator_dashboard")
@invigilator_required
def invigilator_dashboard():

    if session.get("role") != "invigilator":
        return redirect("/")

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




@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")





@app.route("/view_students", methods=["GET", "POST"])
def view_students():

    if session.get("role") != "admin":
        return redirect("/login")

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

@app.route("/view_users")
@admin_required
def view_users():

    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()

    users = conn.execute("SELECT * FROM users").fetchall()

    conn.close()

    return render_template("admin/view_users.html", users=users)

@app.route("/view_courses")
@admin_required
def view_subjects():

    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()

    courses = conn.execute("SELECT * FROM courses").fetchall()

    conn.close()

    return render_template("admin/view_courses.html", courses=courses)


@app.route("/upload_question", methods=["GET","POST"])
@invigilator_required   # 🔥 changed from faculty → invigilator (as per flow)
def upload_question():

    conn = get_db_connection()

    assignment_id = request.args.get("assignment_id")

    assignment = conn.execute("""
    SELECT * FROM exam_assignments WHERE id=?
    """, (assignment_id,)).fetchone()

    if not assignment:
        return "Invalid Assignment ID"

    if request.method == "POST":

        file = request.files["file"]

        if file:

            folder = "uploads/question_papers"
            os.makedirs(folder, exist_ok=True)

            filepath = os.path.join(folder, file.filename)
            file.save(filepath)

            assignment_id = request.args.get("assignment_id")
            conn.execute("""
            INSERT INTO question_papers
            (course_id, exam_id, file_path, assignment_id)
            VALUES ( ?, ?, ?, ?)
            """, (
                assignment["course_id"],
                assignment["exam_id"],
                filepath,
                assignment_id
            ))

            conn.commit()

            return redirect("/invigilator_exams")

    conn.close()

    return render_template(
        "invigilator/upload_question.html",
        assignment_id=assignment_id
    )

@app.route("/upload_model_answer", methods=["GET","POST"])
@invigilator_required
def upload_model_answer():

    conn = get_db_connection()

    assignment_id = request.args.get("assignment_id")

    assignment = conn.execute("""
    SELECT * FROM exam_assignments WHERE id=?
    """, (assignment_id,)).fetchone()

    if not assignment:
        return "Invalid Assignment ID"

    if request.method == "POST":

        file = request.files["file"]

        if file:

            folder = "uploads/model_answers"
            os.makedirs(folder, exist_ok=True)

            filepath = os.path.join(folder, file.filename)
            file.save(filepath)
            
            assignment_id = request.args.get("assignment_id")
            conn.execute("""
            INSERT INTO model_answers
            (course_id, exam_id, file_path, assignment_id)
            VALUES ( ?, ?, ?, ?)
            """, (
                assignment["course_id"],
                assignment["exam_id"],
                filepath,
                assignment_id
            ))

            conn.commit()

            return redirect("/invigilator_exams")

    conn.close()

    return render_template(
        "invigilator/upload_model_answer.html",
        assignment_id=assignment_id
    )

@app.route("/upload_answer", methods=["GET","POST"])
@invigilator_required
def upload_answer():

    conn = get_db_connection()

    assignment_id = request.args.get("assignment_id")

    assignment = conn.execute("""
    SELECT * FROM exam_assignments WHERE id=?
    """, (assignment_id,)).fetchone()

    if not assignment:
        return "Invalid Assignment ID"

    if request.method == "POST":

        student_id = request.form["student_id"]
        file = request.files["file"]

        if file:

            folder = "uploads/student_answers"
            os.makedirs(folder, exist_ok=True)

            filepath = os.path.join(folder, file.filename)
            file.save(filepath)

            conn.execute("""
            INSERT INTO student_answers
            (student_id, course_id, exam_id, file_path, assignment_id)
            VALUES (?, ?, ?, ?, ?)
            """, (
                student_id,
                assignment["course_id"],
                assignment["exam_id"],
                filepath,
                assignment_id
            ))

            conn.commit()

    # ✅ FILTERED STUDENTS (IMPORTANT)
    students = conn.execute("""
    SELECT * FROM students
    WHERE department=? AND year=?
    """, (assignment["department"], assignment["year"])).fetchall()

    conn.close()

    return render_template(
        "invigilator/upload_answer.html",
        students=students,
        assignment_id=assignment_id
    )

@app.route("/view_student_answers")
@faculty_required
def view_student_answers():

    assignment_id = request.args.get("assignment_id")

    conn = get_db_connection()

    answers = conn.execute("""
    SELECT
        sa.id,
        s.roll_no,
        s.student_name,
        c.course_code,
        e.exam_name,
        sa.file_path,
        ev.marks
    FROM student_answers sa
    JOIN students s ON sa.student_id = s.id
    JOIN courses c ON sa.course_id = c.id
    JOIN exams e ON sa.exam_id = e.id
    LEFT JOIN evaluation ev 
        ON sa.id = ev.student_answer_id
    WHERE sa.assignment_id = ?
    """, (assignment_id,)).fetchall()

    conn.close()

    return render_template(
        "faculty/view_student_answers.html",
        answers=answers,
        assignment_id=assignment_id
    )

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

    return render_template(
        "admin/results_dashboard.html",
        results=results
    )

@app.route("/bulk_upload_students", methods=["POST"])
def bulk_upload_students():

    if session.get("role") != "admin":
        return redirect("/login")

    file = request.files["file"]

    if file:

        df = pd.read_excel(file)

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        for index, row in df.iterrows():

            cursor.execute("""
            INSERT OR IGNORE INTO students
            (roll_no, student_name, department, year)
            VALUES (?, ?, ?, ?)
            """, (
                row["roll_no"],
                row["student_name"],
                row["department"],
                str(row["year"])
            ))

        conn.commit()
        conn.close()

    return redirect("/view_students")

@app.route("/delete_student/<int:id>")
def delete_student(id):

    if session.get("role") != "admin":
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM students WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/view_students")

@app.route("/edit_student/<int:id>", methods=["GET", "POST"])
def edit_student(id):

    if session.get("role") != "admin":
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":

        name = request.form["student_name"]
        department = request.form["department"]
        year = request.form["year"]

        cursor.execute("""
        UPDATE students
        SET student_name=?, department=?, year=?
        WHERE id=?
        """, (name, department, year, id))

        conn.commit()
        conn.close()

        return redirect("/view_students")

    cursor.execute("SELECT * FROM students WHERE id=?", (id,))
    student = cursor.fetchone()

    conn.close()

    return render_template("admin/edit_student.html", student=student)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)


@app.route("/create_exam", methods=["GET","POST"])
@admin_required
def create_exam():

    conn = get_db_connection()

    departments = conn.execute(
        "SELECT DISTINCT department FROM students"
    ).fetchall()

    courses = conn.execute("SELECT * FROM courses").fetchall()
    exams = conn.execute("SELECT * FROM exams").fetchall()

    if request.method == "POST":

        conn.execute("""
        INSERT INTO exam_assignments (department, year, course_id, exam_id)
        VALUES (?, ?, ?, ?)
        """, (
            request.form["department"],
            request.form["year"],
            request.form["course"],
            request.form["exam"]
        ))

        conn.commit()

    conn.close()

    return render_template("admin/create_exam.html",
                           departments=departments,
                           courses=courses,
                           exams=exams)


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


@app.route("/manage_exam/<int:id>")
@invigilator_required
def manage_exam(id):

    return render_template("invigilator/manage_exam.html", id=id)

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

        conn.commit()

        return redirect("/admin_dashboard")

    conn.close()

    return render_template(
        "admin/assign_faculty.html",
        faculty=faculty,
        assignment_id=id
    )

@app.route("/faculty_tasks")
@faculty_required
def faculty_tasks():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    SELECT ea.*, c.course_name, e.exam_name
    FROM exam_assignments ea
    JOIN courses c ON ea.course_id = c.id
    JOIN exams e ON ea.exam_id = e.id
    WHERE ea.assigned_faculty = ?
    """, (session["user_id"],))

    tasks = cursor.fetchall()

    conn.close()

    return render_template("faculty/tasks.html", tasks=tasks)

@app.route("/delete_exam/<int:id>")
@admin_required
def delete_exam(id):

    conn = get_db_connection()

    # ❗ First delete dependent data (IMPORTANT)
    conn.execute("DELETE FROM student_answers WHERE assignment_id=?", (id,))
    conn.execute("DELETE FROM question_papers WHERE assignment_id=?", (id,))
    conn.execute("DELETE FROM model_answers WHERE assignment_id=?", (id,))
    conn.execute("DELETE FROM exam_assignments WHERE id=?", (id,))

    conn.commit()
    conn.close()

    flash("❌ Exam deleted successfully!", "success")

    return redirect("/admin_dashboard")

if __name__ == "__main__":
    app.run(debug=True)