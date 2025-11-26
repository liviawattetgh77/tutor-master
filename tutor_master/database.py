import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional

DB_PATH = Path(__file__).resolve().parent / "tutor_master.db"


COURSE_SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    course_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    course_type TEXT NOT NULL,
    grade_level TEXT NOT NULL,
    is_trial INTEGER DEFAULT 0,
    students TEXT NOT NULL,
    notes TEXT DEFAULT '',
    location TEXT DEFAULT '',
    subject TEXT DEFAULT ''
);
"""


GRADE_LEVELS = [
    "初一",
    "初二",
    "初三",
    "高一",
    "高二",
    "高三",
]


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize(db_path: Path = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(COURSE_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def list_courses(db_path: Path = DB_PATH) -> List[sqlite3.Row]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM courses ORDER BY course_date, start_time"
        ).fetchall()
        return list(rows)
    finally:
        conn.close()


def get_course(course_id: int, db_path: Path = DB_PATH) -> Optional[sqlite3.Row]:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM courses WHERE id = ?", (course_id,)
        ).fetchone()
        return row
    finally:
        conn.close()


def add_course(
    *,
    title: str,
    course_date: str,
    start_time: str,
    end_time: str,
    course_type: str,
    grade_level: str,
    is_trial: bool,
    students: Iterable[str],
    notes: str = "",
    location: str = "",
    subject: str = "",
    db_path: Path = DB_PATH,
) -> int:
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO courses (
                title, course_date, start_time, end_time, course_type,
                grade_level, is_trial, students, notes, location, subject
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                course_date,
                start_time,
                end_time,
                course_type,
                grade_level,
                1 if is_trial else 0,
                ", ".join(students),
                notes,
                location,
                subject,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def update_course(
    course_id: int,
    *,
    title: str,
    course_date: str,
    start_time: str,
    end_time: str,
    course_type: str,
    grade_level: str,
    is_trial: bool,
    students: Iterable[str],
    notes: str = "",
    location: str = "",
    subject: str = "",
    db_path: Path = DB_PATH,
) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            UPDATE courses SET
                title = ?,
                course_date = ?,
                start_time = ?,
                end_time = ?,
                course_type = ?,
                grade_level = ?,
                is_trial = ?,
                students = ?,
                notes = ?,
                location = ?,
                subject = ?
            WHERE id = ?
            """,
            (
                title,
                course_date,
                start_time,
                end_time,
                course_type,
                grade_level,
                1 if is_trial else 0,
                ", ".join(students),
                notes,
                location,
                subject,
                course_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_course(course_id: int, db_path: Path = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()
    finally:
        conn.close()


def sample_seed(db_path: Path = DB_PATH) -> None:
    if DB_PATH.exists():
        # avoid overriding user data
        return
    initialize(db_path)
    add_course(
        title="数学强化",
        course_date="2025-10-06",
        start_time="08:00",
        end_time="10:00",
        course_type="1v1",
        grade_level="初三",
        is_trial=False,
        students=["张三"],
        subject="数学",
    )
    add_course(
        title="英语提升",
        course_date="2025-10-06",
        start_time="10:20",
        end_time="12:00",
        course_type="1v1",
        grade_level="高一",
        is_trial=False,
        students=["李四"],
        subject="英语",
    )
    add_course(
        title="物理试听",
        course_date="2025-10-07",
        start_time="18:30",
        end_time="20:00",
        course_type="1v1",
        grade_level="初一",
        is_trial=True,
        students=["王五"],
        subject="物理",
    )
