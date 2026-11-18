"""
MARKS & RESULT ANALYZER
Single-file Python project using Tkinter (GUI) and SQLite (database).

Run:
    python marks_result_analyzer.py

Optional PDF export:
    pip install reportlab
"""
import csv
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

DB_NAME = "marks_analyzer.db"
PASS_MARK = 40

GRADE_TABLE = [
    (90, "O", 10), (80, "A+", 9), (70, "A", 8),
    (60, "B+", 7), (50, "B", 6), (40, "C", 5), (0, "F", 0)
]


# ---------------- DATABASE ----------------
def connect():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reg_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                semester INTEGER NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS marks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                marks REAL NOT NULL,
                max_marks REAL NOT NULL,
                credits REAL NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE(student_id, subject)
            )
        """)
        con.execute("PRAGMA foreign_keys = ON")


def add_student(reg_no, name, department, semester):
    with connect() as con:
        con.execute(
            "INSERT INTO students(reg_no,name,department,semester) VALUES(?,?,?,?)",
            (reg_no, name, department, semester)
        )


def get_students():
    with connect() as con:
        return con.execute(
            "SELECT id,reg_no,name,department,semester FROM students ORDER BY name"
        ).fetchall()


def add_mark(student_id, subject, marks, maximum, credits):
    if maximum <= 0 or marks < 0 or marks > maximum or credits <= 0:
        raise ValueError("Enter valid marks, maximum marks and credits.")
    with connect() as con:
        con.execute(
            """INSERT INTO marks(student_id,subject,marks,max_marks,credits)
               VALUES(?,?,?,?,?)
               ON CONFLICT(student_id,subject) DO UPDATE SET
               marks=excluded.marks, max_marks=excluded.max_marks,
               credits=excluded.credits""",
            (student_id, subject, marks, maximum, credits)
        )


def get_all_marks():
    with connect() as con:
        return con.execute("""
            SELECT student_id,subject,marks,max_marks,credits
            FROM marks ORDER BY subject
        """).fetchall()


def delete_student(student_id):
    with connect() as con:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("DELETE FROM students WHERE id=?", (student_id,))


# ---------------- RESULT CALCULATIONS ----------------
def get_grade(percentage):
    for minimum, grade, points in GRADE_TABLE:
        if percentage >= minimum:
            return grade, points
    return "F", 0


def calculate_result(subject_rows):
    if not subject_rows:
        return None

    total = sum(row[2] for row in subject_rows)
    maximum = sum(row[3] for row in subject_rows)
    if maximum <= 0:
        return None

    percentage = total / maximum * 100
    credit_total = sum(row[4] for row in subject_rows)
    weighted_points = 0
    failed_subjects = []

    for row in subject_rows:
        subject, marks, max_marks, credits = row[1], row[2], row[3], row[4]
        subject_percentage = marks / max_marks * 100
        _, points = get_grade(subject_percentage)
        weighted_points += points * credits
        if subject_percentage < PASS_MARK:
            failed_subjects.append(subject)

    gpa = weighted_points / credit_total if credit_total else 0
    overall_grade, _ = get_grade(percentage)

    return {
        "total": total, "maximum": maximum,
        "percentage": percentage, "gpa": gpa,
        "grade": "F" if failed_subjects else overall_grade,
        "status": "FAIL" if failed_subjects else "PASS",
        "failed": failed_subjects
    }


def build_results():
    students = get_students()
    marks = get_all_marks()
    results = []

    for student in students:
        sid, reg, name, dept, sem = student
        student_marks = [m for m in marks if m[0] == sid]
        result = calculate_result(student_marks)
        if result:
            results.append({
                "id": sid, "reg_no": reg, "name": name,
                "department": dept, "semester": sem, **result
            })

    results.sort(key=lambda item: (-item["percentage"], item["name"].lower()))
    previous_percentage = None
    rank = 0
    for position, result in enumerate(results, start=1):
        if result["percentage"] != previous_percentage:
            rank = position
            previous_percentage = result["percentage"]
        result["rank"] = rank
    return results


# ---------------- TKINTER APPLICATION ----------------
class MarksAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Marks & Result Analyzer")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self.root.configure(bg="#f3f5fa")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=25, font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

        heading = tk.Label(
            root, text="MARKS & RESULT ANALYZER",
            font=("Arial", 20, "bold"), bg="#1f2a44", fg="white", pady=15
        )
        heading.pack(fill="x")

        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self.dashboard_tab = ttk.Frame(self.tabs)
        self.students_tab = ttk.Frame(self.tabs)
        self.marks_tab = ttk.Frame(self.tabs)
        self.results_tab = ttk.Frame(self.tabs)
        self.toppers_tab = ttk.Frame(self.tabs)
        self.reports_tab = ttk.Frame(self.tabs)

        for tab, title in [
            (self.dashboard_tab, "Dashboard"),
            (self.students_tab, "Students"),
            (self.marks_tab, "Enter Marks"),
            (self.results_tab, "Results"),
            (self.toppers_tab, "Toppers"),
            (self.reports_tab, "Reports")
        ]:
            self.tabs.add(tab, text=title)

        self.create_dashboard()
        self.create_students()
        self.create_marks()
        self.create_results()
        self.create_toppers()
        self.create_reports()
        self.refresh_all()

        self.tabs.bind("<<NotebookTabChanged>>", lambda event: self.refresh_all())

    def create_table(self, parent, columns, widths, height=12):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
        for column, width in zip(columns, widths):
            tree.heading(column, text=column)
            tree.column(column, width=width, anchor="center")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        tree.tag_configure("PASS", background="#e6f6ea")
        tree.tag_configure("FAIL", background="#fde8e8")
        return tree

    def create_dashboard(self):
        ttk.Label(self.dashboard_tab, text="Project Overview",
                  font=("Arial", 16, "bold")).pack(pady=18)
        self.dashboard_info = ttk.Label(
            self.dashboard_tab, text="", font=("Arial", 13), justify="left"
        )
        self.dashboard_info.pack(pady=15)
        ttk.Button(self.dashboard_tab, text="Refresh Dashboard",
                   command=self.refresh_all).pack(pady=10)

    def create_students(self):
        form = ttk.LabelFrame(self.students_tab, text="Add Student")
        form.pack(fill="x", padx=15, pady=15)

        self.reg_entry = self.add_field(form, "Register Number", 0, 0)
        self.name_entry = self.add_field(form, "Student Name", 0, 2)
        self.dept_entry = self.add_field(form, "Department", 1, 0)
        self.sem_entry = self.add_field(form, "Semester", 1, 2)

        ttk.Button(form, text="Add Student",
                   command=self.save_student).grid(row=2, column=1, pady=12)
        ttk.Button(form, text="Delete Selected",
                   command=self.remove_student).grid(row=2, column=2, pady=12)

        self.student_tree = self.create_table(
            self.students_tab,
            ("ID", "Register No", "Name", "Department", "Semester"),
            (55, 150, 220, 150, 90)
        )

    def add_field(self, parent, label, row, col):
        ttk.Label(parent, text=label).grid(row=row, column=col, padx=8, pady=8, sticky="w")
        entry = ttk.Entry(parent, width=25)
        entry.grid(row=row, column=col + 1, padx=8, pady=8)
        return entry

    def save_student(self):
        reg = self.reg_entry.get().strip()
        name = self.name_entry.get().strip()
        dept = self.dept_entry.get().strip()
        sem = self.sem_entry.get().strip()

        if not all([reg, name, dept, sem]):
            messagebox.showwarning("Missing Details", "Please fill all student details.")
            return
        try:
            semester = int(sem)
            if semester <= 0:
                raise ValueError
            add_student(reg, name, dept, semester)
            for entry in (self.reg_entry, self.name_entry, self.dept_entry, self.sem_entry):
                entry.delete(0, tk.END)
            self.refresh_all()
            messagebox.showinfo("Success", "Student added successfully.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate", "This register number already exists.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Semester must be a positive number.")

    def remove_student(self):
        selected = self.student_tree.selection()
        if not selected:
            messagebox.showwarning("Select Student", "Select a student to delete.")
            return
        student_id = self.student_tree.item(selected[0])["values"][0]
        if messagebox.askyesno("Confirm", "Delete this student and their marks?"):
            delete_student(student_id)
            self.refresh_all()

    def create_marks(self):
        form = ttk.LabelFrame(self.marks_tab, text="Enter Subject Marks")
        form.pack(fill="x", padx=15, pady=15)

        ttk.Label(form, text="Student").grid(row=0, column=0, padx=8, pady=8)
        self.student_combo = ttk.Combobox(form, width=35, state="readonly")
        self.student_combo.grid(row=0, column=1, padx=8, pady=8)

        self.subject_entry = self.add_field(form, "Subject", 0, 2)
        self.mark_entry = self.add_field(form, "Marks Obtained", 1, 0)
        self.max_entry = self.add_field(form, "Maximum Marks", 1, 2)
        self.credit_entry = self.add_field(form, "Credits", 2, 0)

        ttk.Button(form, text="Save Marks",
                   command=self.save_marks).grid(row=2, column=3, padx=10, pady=10)

        self.marks_tree = self.create_table(
            self.marks_tab,
            ("Student", "Subject", "Marks", "Maximum", "Credits"),
            (220, 180, 100, 100, 100)
        )

    def save_marks(self):
        selection = self.student_combo.get()
        if not selection:
            messagebox.showwarning("Select Student", "Please select a student.")
            return
        try:
            student_id = int(selection.split(" | ")[0])
            subject = self.subject_entry.get().strip()
            marks = float(self.mark_entry.get())
            maximum = float(self.max_entry.get())
            credits = float(self.credit_entry.get())
            if not subject:
                raise ValueError
            add_mark(student_id, subject, marks, maximum, credits)
            for entry in (self.subject_entry, self.mark_entry, self.max_entry, self.credit_entry):
                entry.delete(0, tk.END)
            self.refresh_all()
            messagebox.showinfo("Saved", "Marks saved successfully.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Enter valid subject, marks, maximum and credits.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Database Error", "Unable to save these marks.")

    def create_results(self):
        ttk.Label(self.results_tab, text="Student Results",
                  font=("Arial", 15, "bold")).pack(pady=8)
        self.results_tree = self.create_table(
            self.results_tab,
            ("Rank", "Register No", "Name", "Department", "Sem",
             "Total", "Percentage", "GPA", "Grade", "Status"),
            (55, 115, 150, 100, 50, 90, 95, 65, 65, 75)
        )

    def create_toppers(self):
        ttk.Label(self.toppers_tab, text="Top 10 Passed Students",
                  font=("Arial", 15, "bold")).pack(pady=8)
        self.toppers_tree = self.create_table(
            self.toppers_tab,
            ("Rank", "Register No", "Name", "Department", "Percentage", "GPA"),
            (60, 140, 200, 130, 120, 100)
        )

    def create_reports(self):
        ttk.Label(self.reports_tab, text="Export Result Reports",
                  font=("Arial", 15, "bold")).pack(pady=20)
        ttk.Button(self.reports_tab, text="Export Results to CSV",
                   command=self.export_csv_file).pack(pady=12)
        ttk.Button(self.reports_tab, text="Export Results to PDF",
                   command=self.export_pdf_file).pack(pady=12)
        ttk.Label(self.reports_tab,
                  text="PDF export requires ReportLab: pip install reportlab").pack(pady=8)

    def refresh_all(self):
        students = get_students()
        marks = get_all_marks()
        results = build_results()

        if hasattr(self, "student_tree"):
            self.student_tree.delete(*self.student_tree.get_children())
            for row in students:
                self.student_tree.insert("", "end", values=row)

        if hasattr(self, "student_combo"):
            self.student_combo["values"] = [
                f"{s[0]} | {s[2]} ({s[1]})" for s in students
            ]

        if hasattr(self, "marks_tree"):
            self.marks_tree.delete(*self.marks_tree.get_children())
            student_names = {s[0]: s[2] for s in students}
            for sid, subject, mark, maximum, credits in marks:
                self.marks_tree.insert("", "end", values=(
                    student_names.get(sid, "Unknown"), subject, mark, maximum, credits
                ))

        if hasattr(self, "results_tree"):
            self.results_tree.delete(*self.results_tree.get_children())
            for r in results:
                self.results_tree.insert("", "end", tags=(r["status"],), values=(
                    r["rank"], r["reg_no"], r["name"], r["department"], r["semester"],
                    f'{r["total"]:g}/{r["maximum"]:g}', f'{r["percentage"]:.2f}%',
                    f'{r["gpa"]:.2f}', r["grade"], r["status"]
                ))

        if hasattr(self, "toppers_tree"):
            self.toppers_tree.delete(*self.toppers_tree.get_children())
            toppers = [r for r in results if r["status"] == "PASS"][:10]
            for r in toppers:
                self.toppers_tree.insert("", "end", values=(
                    r["rank"], r["reg_no"], r["name"], r["department"],
                    f'{r["percentage"]:.2f}%', f'{r["gpa"]:.2f}'
                ))

        if hasattr(self, "dashboard_info"):
            passed = sum(r["status"] == "PASS" for r in results)
            average = sum(r["percentage"] for r in results) / len(results) if results else 0
            pass_rate = passed / len(results) * 100 if results else 0
            self.dashboard_info.config(text=(
                f"Total Students: {len(students)}\\n"
                f"Results Available: {len(results)}\\n"
                f"Passed Students: {passed}\\n"
                f"Pass Percentage: {pass_rate:.2f}%\\n"
                f"Average Percentage: {average:.2f}%"
            ))

    def export_csv_file(self):
        results = build_results()
        if not results:
            messagebox.showwarning("No Results", "There are no results to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        headers = ["Rank", "Register No", "Name", "Department", "Semester",
                   "Total", "Maximum", "Percentage", "GPA", "Grade", "Status"]
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            for r in results:
                writer.writerow([
                    r["rank"], r["reg_no"], r["name"], r["department"], r["semester"],
                    r["total"], r["maximum"], f'{r["percentage"]:.2f}',
                    f'{r["gpa"]:.2f}', r["grade"], r["status"]
                ])
        messagebox.showinfo("Exported", "CSV report saved successfully.")

    def export_pdf_file(self):
        results = build_results()
        if not results:
            messagebox.showwarning("No Results", "There are no results to export.")
            return
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            messagebox.showerror(
                "ReportLab Required",
                "Install ReportLab first using: pip install reportlab"
            )
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return

        document = SimpleDocTemplate(path, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        data = [["Rank", "Register No", "Name", "Department", "Sem",
                 "Total", "Percentage", "GPA", "Grade", "Status"]]
        for r in results:
            data.append([
                r["rank"], r["reg_no"], r["name"], r["department"], r["semester"],
                f'{r["total"]:g}/{r["maximum"]:g}', f'{r["percentage"]:.2f}%',
                f'{r["gpa"]:.2f}', r["grade"], r["status"]
            ])
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2a44")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ]))
        story = [Paragraph("Marks & Result Analyzer", styles["Title"]), Spacer(1, 12), table]
        document.build(story)
        messagebox.showinfo("Exported", "PDF report saved successfully.")


if __name__ == "__main__":
    initialize_database()
    root = tk.Tk()
    app = MarksAnalyzerApp(root)
    root.mainloop()
