import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# USERS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT UNIQUE,
password TEXT,
role TEXT
)
""")

# COURSES TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS courses (
id INTEGER PRIMARY KEY AUTOINCREMENT,
course_code TEXT UNIQUE,
course_name TEXT
)
""")
# DEPARTMENT TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS departments (
id INTEGER PRIMARY KEY AUTOINCREMENT,
department TEXT UNIQUE
)
""")

# STUDENTS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
id INTEGER PRIMARY KEY AUTOINCREMENT,
roll_no TEXT UNIQUE,
student_name TEXT,
department TEXT,
year TEXT
)
""")

# EXAMS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS exams (
id INTEGER PRIMARY KEY AUTOINCREMENT,
exam_name TEXT
)
""")

# QUESTION PAPERS
cursor.execute("""
CREATE TABLE IF NOT EXISTS question_papers (
id INTEGER PRIMARY KEY AUTOINCREMENT,
course_id INTEGER,
exam_id INTEGER,
file_path TEXT
)
""")

# MODEL ANSWERS
cursor.execute("""
CREATE TABLE IF NOT EXISTS model_answers (
id INTEGER PRIMARY KEY AUTOINCREMENT,
course_id INTEGER,
exam_id INTEGER,
file_path TEXT
)
""")

# STUDENT ANSWERS
cursor.execute("""
CREATE TABLE IF NOT EXISTS student_answers (
id INTEGER PRIMARY KEY AUTOINCREMENT,
student_id INTEGER,
course_id INTEGER,
exam_id INTEGER,
file_path TEXT
)
""")

# EVALUATION TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS evaluation (
id INTEGER PRIMARY KEY AUTOINCREMENT,
student_answer_id INTEGER,
marks INTEGER,
comments TEXT,
evaluator_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS exam_assignments (
id INTEGER PRIMARY KEY AUTOINCREMENT,
department TEXT,
year TEXT,
course_id INTEGER,
exam_id INTEGER,
status TEXT DEFAULT 'created',
assigned_faculty INTEGER
)
""")

# 🟢 STEP 1: SAFE COLUMN ADD FUNCTION

def add_column_if_not_exists(cursor, table, column_def):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
    except sqlite3.OperationalError:
        pass  # Column already exists


# 🟢 STEP 2: APPLY TO ALL TABLES

# ✅ ADD assignment_id SAFELY

add_column_if_not_exists(cursor, "student_answers", "assignment_id INTEGER")
add_column_if_not_exists(cursor, "question_papers", "assignment_id INTEGER")
add_column_if_not_exists(cursor, "model_answers", "assignment_id INTEGER")

# ---------------------------------------------------
# DEFAULT USERS
# ---------------------------------------------------

cursor.execute("INSERT OR IGNORE INTO users VALUES (1,'admin','123','admin')")
cursor.execute("INSERT OR IGNORE INTO users VALUES (2,'faculty1','123','faculty')")
cursor.execute("INSERT OR IGNORE INTO users VALUES (3,'invigilator1','123','invigilator')")

# ---------------------------------------------------
# PREDEFINED COURSES
# ---------------------------------------------------

cursor.execute("INSERT OR IGNORE INTO courses VALUES (1,'CM201','Data Structures')")
cursor.execute("INSERT OR IGNORE INTO courses VALUES (2,'CM202','Database Management')")
cursor.execute("INSERT OR IGNORE INTO courses VALUES (3,'CM203','Operating Systems')")
cursor.execute("INSERT OR IGNORE INTO courses VALUES (4,'CM204','Computer Networks')")
cursor.execute("INSERT OR IGNORE INTO courses VALUES (5,'CM205','Software Engineering')")
cursor.execute("INSERT OR IGNORE INTO courses VALUES (6,'CM206','Advanced Computer Network')")

# ---------------------------------------------------
# PREDEFINED STUDENTS
# ---------------------------------------------------

cursor.execute("INSERT OR IGNORE INTO students VALUES (1,'CSE001','Rahul Sharma','Computer Engineering','1')")
cursor.execute("INSERT OR IGNORE INTO students VALUES (2,'CSE002','Priya Singh','Computer Engineering','2')")
cursor.execute("INSERT OR IGNORE INTO students VALUES (3,'CSE003','Amit Patel','Computer Engineering','3')")
cursor.execute("INSERT OR IGNORE INTO students VALUES (4,'CSE004','Sneha Verma','Mechanical Engineering','3')")
cursor.execute("INSERT OR IGNORE INTO students VALUES (5,'CSE005','Arjun Gupta','Electronics Engineering','3')")

# ---------------------------------------------------
# PREDEFINED EXAMS
# ---------------------------------------------------

cursor.execute("INSERT OR IGNORE INTO exams VALUES (1,'Progressive Test 1')")
cursor.execute("INSERT OR IGNORE INTO exams VALUES (2,'Progressive Test 2')")
cursor.execute("INSERT OR IGNORE INTO exams VALUES (3,'Semester Exam')")
cursor.execute("INSERT OR IGNORE INTO exams VALUES (4,'Practical Exam')")
cursor.execute("INSERT OR IGNORE INTO exams VALUES (5,'Viva')")

# ---------------------------------------------------
# PREDEFINED DEPARTMENTS
# ---------------------------------------------------
cursor.execute("INSERT OR IGNORE INTO departments (department) VALUES ('Computer Engineering')")
cursor.execute("INSERT OR IGNORE INTO departments (department) VALUES ('Civil Engineering')")
cursor.execute("INSERT OR IGNORE INTO departments (department) VALUES ('Electronics Engineering')")
cursor.execute("INSERT OR IGNORE INTO departments (department) VALUES ('Mechanical Engineering')")

conn.commit()
conn.close()

print("Database created successfully with A NEW sample data")