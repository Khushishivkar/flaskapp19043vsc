from flask import Flask, render_template, request, redirect, session, Response
import sqlite3
from datetime import date
import csv

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE CONNECTION ----------------
def get_db():
    conn = sqlite3.connect("attendance.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- LOGIN PAGE ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # ADMIN LOGIN
        if username == "admin" and password == "admin":
            session["admin"] = True
            return redirect("/admin")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM students WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session["user"] = user["rollno"]
            return redirect("/dashboard")

    return render_template("login.html")

# ---------------- REGISTER PAGE ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        course = request.form["course"]

        conn = get_db()
        conn.execute(
            "INSERT INTO students(username,email,password,course) VALUES (?,?,?,?)",
            (username, email, password, course)
        )
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template("register.html")

# ---------------- STUDENT DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    rollno = session["user"]
    conn = get_db()

    student = conn.execute(
        "SELECT * FROM students WHERE rollno=?",
        (rollno,)
    ).fetchone()

    attendance = conn.execute(
        "SELECT * FROM attendance WHERE rollno=? ORDER BY date DESC",
        (rollno,)
    ).fetchall()

    # Attendance summary
    total = len(attendance)
    present = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE rollno=? AND status='Present'",
        (rollno,)
    ).fetchone()[0]
    absent = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE rollno=? AND status='Absent'",
        (rollno,)
    ).fetchone()[0]
    percentage = round((present / total) * 100, 2) if total > 0 else 0

    conn.close()

    return render_template(
        "dashboard.html",
        student=student,
        attendance=attendance,
        total=total,
        present=present,
        absent=absent,
        percentage=percentage
    )

# ---------------- ADMIN PANEL ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "admin" not in session:
        return redirect("/")

    conn = get_db()

    if request.method == "POST":
        rollno = request.form["rollno"]
        status = request.form["status"]
        today = date.today()

        # Prevent duplicate attendance on the same date
        existing = conn.execute(
            "SELECT * FROM attendance WHERE rollno=? AND date=?",
            (rollno, today)
        ).fetchone()

        if not existing:
            student = conn.execute(
                "SELECT username FROM students WHERE rollno=?",
                (rollno,)
            ).fetchone()
            if student:
                name = student["username"]
                conn.execute(
                    "INSERT INTO attendance(rollno,name,status,date) VALUES (?,?,?,?)",
                    (rollno, name, status, today)
                )
                conn.commit()

    students = conn.execute("SELECT * FROM students").fetchall()
    records = conn.execute("SELECT * FROM attendance ORDER BY date DESC").fetchall()
    conn.close()

    return render_template("admin.html", students=students, records=records)

# ---------------- DELETE STUDENT ----------------
@app.route("/delete/<int:rollno>")
def delete(rollno):
    conn = get_db()
    conn.execute("DELETE FROM students WHERE rollno=?", (rollno,))
    conn.commit()
    conn.close()
    return redirect("/admin")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- DOWNLOAD ATTENDANCE REPORT (CSV) ----------------
@app.route("/download")
def download():
    if "admin" not in session:
        return redirect("/")

    conn = get_db()
    records = conn.execute("SELECT * FROM attendance ORDER BY date DESC").fetchall()
    conn.close()

    def generate():
        header = ["Roll No", "Name", "Status", "Date"]
        yield ",".join(header) + "\n"
        for r in records:
            row = [str(r["rollno"]), r["name"], r["status"], str(r["date"])]
            yield ",".join(row) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=attendance_report.csv"}
    )

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True)