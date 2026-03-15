from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import sqlite3
from config import Config
import os


app = Flask(__name__)
app.config.from_object(Config)


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


@app.route("/admin_dashboard")
def admin_dashboard():
    return render_template("admin/admin_dashboard.html")


@app.route("/faculty_dashboard")
def faculty_dashboard():
    return render_template("faculty/faculty_dashboard.html")


@app.route("/invigilator_dashboard")
def invigilator_dashboard():
    return render_template("invigilator/invigilator_dashboard.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/view_students")
def view_students():

    conn = get_db_connection()

    students = conn.execute(
        "SELECT * FROM students"
    ).fetchall()

    conn.close()

    return render_template(
        "admin/view_students.html",
        students=students
    )

@app.route("/upload_question", methods=["GET","POST"])
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
def view_users():

    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()

    users = conn.execute("SELECT * FROM users").fetchall()

    conn.close()

    return render_template("admin/view_users.html", users=users)

@app.route("/view_courses")
def view_subjects():

    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()

    courses = conn.execute("SELECT * FROM courses").fetchall()

    conn.close()

    return render_template("admin/view_courses.html", courses=courses)

if __name__ == "__main__":
    app.run(debug=True)