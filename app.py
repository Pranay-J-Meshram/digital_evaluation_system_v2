from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import sqlite3
from config import Config
import os
from functools import wraps
from flask import session, redirect, url_for
import pandas as pd


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

    cursor.execute("SELECT COUNT(*) as total_answers FROM student_answers")
    total_answers = cursor.fetchone()["total_answers"]

    cursor.execute("SELECT COUNT(*) as evaluated FROM evaluation")
    evaluated = cursor.fetchone()["evaluated"]

    pending = total_answers - evaluated

    conn.close()

    return render_template(
        "admin/admin_dashboard.html",
        total_students=total_students,
        total_courses=total_courses,
        total_exams=total_exams,
        total_answers=total_answers,
        evaluated=evaluated,
        pending=pending
    )


@app.route('/faculty_dashboard')
@faculty_required
def faculty_dashboard():
     if "role" not in session or session["role"] != "faculty":
        return redirect("/")
     return render_template("faculty/faculty_dashboard.html")
    


@app.route('/invigilator_dashboard')
@invigilator_required
def invigilator_dashboard():
     if "role" not in session or session["role"] != "invigilator":
        return redirect("/")
     return render_template("invigilator/invigilator_dashboard.html")
     
    
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

@app.route("/upload_question", methods=["GET","POST"])
@admin_required
def upload_question():

    conn = get_db_connection()

    if request.method == "POST":

        course_id = request.form["course_id"]
        exam_id = request.form["exam_id"]
        file = request.files["file"]

        if file:

            folder = "uploads/question_papers"
            os.makedirs(folder, exist_ok=True)

            filepath = os.path.join(folder, file.filename)
            file.save(filepath)

            conn.execute("""
            INSERT INTO question_papers
            (course_id,exam_id,file_path)
            VALUES (?,?,?)
            """,(course_id,exam_id,filepath))

            conn.commit()

            return redirect("/admin_dashboard")

    courses = conn.execute("SELECT * FROM courses").fetchall()
    exams = conn.execute("SELECT * FROM exams").fetchall()

    conn.close()

    return render_template(
        "admin/upload_question.html",
        courses=courses,
        exams=exams
    )

@app.route("/upload_model_answer", methods=["GET","POST"])
@admin_required
def upload_model_answer():

    conn = get_db_connection()

    if request.method == "POST":

        course_id = request.form["course_id"]
        exam_id = request.form["exam_id"]
        file = request.files["file"]

        if file:

            folder = "uploads/model_answers"
            os.makedirs(folder, exist_ok=True)

            filepath = os.path.join(folder, file.filename)
            file.save(filepath)

            conn.execute("""
            INSERT INTO model_answers
            (course_id,exam_id,file_path)
            VALUES (?,?,?)
            """,(course_id,exam_id,filepath))

            conn.commit()

            return redirect("/admin_dashboard")

    courses = conn.execute("SELECT * FROM courses").fetchall()
    exams = conn.execute("SELECT * FROM exams").fetchall()

    conn.close()

    return render_template(
        "admin/upload_model_answer.html",
        courses=courses,
        exams=exams
    )

@app.route("/upload_answer", methods=["GET","POST"])
@invigilator_required
def upload_answer():

    conn = get_db_connection()

    if request.method == "POST":

        student_id = request.form["student_id"]
        course_id = request.form["course_id"]
        exam_id = request.form["exam_id"]
        file = request.files["file"]

        if file:

            folder = "uploads/student_answers"
            os.makedirs(folder, exist_ok=True)

            filepath = os.path.join(folder, file.filename)
            file.save(filepath)

            conn.execute("""
            INSERT INTO student_answers
            (student_id,course_id,exam_id,file_path)
            VALUES (?,?,?,?)
            """,(student_id,course_id,exam_id,filepath))

            conn.commit()

            return redirect("/invigilator_dashboard")

    students = conn.execute("SELECT * FROM students").fetchall()
    courses = conn.execute("SELECT * FROM courses").fetchall()
    exams = conn.execute("SELECT * FROM exams").fetchall()

    conn.close()

    return render_template(
        "invigilator/upload_answer.html",
        students=students,
        courses=courses,
        exams=exams
    )

@app.route("/add_exam", methods=["GET", "POST"])
def add_exam():

    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()

    if request.method == "POST":

        exam_id = request.form["exam_id"]

        # here you can save selected exam if needed
        conn.execute(
            "INSERT INTO exams_selected (exam_id) VALUES (?)",
            (exam_id,)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin_dashboard"))

    exams = conn.execute("SELECT * FROM exams").fetchall()
    conn.close()

    return render_template("admin/add_exam.html", exams=exams)

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

@app.route("/view_student_answers")
@faculty_required
def view_student_answers():

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
        "faculty/view_student_answers.html",
        answers=answers
    )

@app.route("/evaluate/<int:answer_id>", methods=["GET","POST"])
@faculty_required
def evaluate(answer_id):

    conn = get_db_connection()

    if request.method == "POST":

        marks = request.form["marks"]
        comments = request.form["comments"]

        conn.execute("""
        INSERT INTO evaluation
        (student_answer_id,marks,comments,evaluator_id)
        VALUES (?,?,?,?)
        """,(answer_id,marks,comments,1))

        conn.commit()

        return redirect("/view_student_answers")

    answer = conn.execute("""
    SELECT
    student_answers.file_path AS student_file,
    model_answers.file_path AS model_file,
    students.student_name,
    courses.course_code,
    exams.exam_name
    FROM student_answers
    JOIN students ON student_answers.student_id = students.id
    JOIN courses ON student_answers.course_id = courses.id
    JOIN exams ON student_answers.exam_id = exams.id
    LEFT JOIN model_answers
    ON student_answers.course_id = model_answers.course_id
    AND student_answers.exam_id = model_answers.exam_id
    WHERE student_answers.id = ?
    """,(answer_id,)).fetchone()

    conn.close()

    return render_template(
        "faculty/evaluate.html",
        answer=answer,
        answer_id=answer_id
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

if __name__ == "__main__":
    app.run(debug=True)