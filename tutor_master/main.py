import datetime as dt
import tkinter as tk
from tkinter import messagebox, ttk

from . import database
from .database import add_course, delete_course, get_course, list_courses, update_course
from .salary import calculate_salary, filter_courses_for_month
from .scheduling import (
    Course,
    DEFAULT_SLOTS,
    GRADE_COLORS,
    CourseMonth,
    find_course_month,
    group_by_week,
)

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 720
START_MINUTES = 7 * 60
END_MINUTES = 22 * 60
PIXELS_PER_MIN = 1.2


class CourseDialog(tk.Toplevel):
    def __init__(self, master, title: str, initial=None, on_save=None):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.on_save = on_save
        self.initial = initial or {}
        self._build()

    def _build(self):
        labels = [
            "课程名称",
            "日期 (YYYY-MM-DD)",
            "开始时间 (HH:MM)",
            "结束时间 (HH:MM)",
            "课程性质",
            "年级段",
            "是否试听 (0/1)",
            "学生（用逗号分隔）",
            "科目",
            "地点",
            "备注",
        ]
        self.entries = {}
        values = [
            self.initial.get("title", ""),
            self.initial.get("course_date", dt.date.today().isoformat()),
            self.initial.get("start_time", "08:00"),
            self.initial.get("end_time", "10:00"),
            self.initial.get("course_type", "1v1"),
            self.initial.get("grade_level", "初一"),
            str(int(self.initial.get("is_trial", False))),
            self.initial.get("students", ""),
            self.initial.get("subject", ""),
            self.initial.get("location", ""),
            self.initial.get("notes", ""),
        ]
        for i, (label, value) in enumerate(zip(labels, values)):
            tk.Label(self, text=label).grid(row=i, column=0, sticky=tk.W, padx=8, pady=4)
            entry = tk.Entry(self, width=40)
            entry.insert(0, value)
            entry.grid(row=i, column=1, padx=8, pady=4)
            self.entries[label] = entry

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=len(labels), column=0, columnspan=2, pady=8)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="保存", command=self._save).pack(side=tk.RIGHT, padx=4)

    def _save(self):
        try:
            payload = {
                "title": self.entries["课程名称"].get(),
                "course_date": self.entries["日期 (YYYY-MM-DD)"].get(),
                "start_time": self.entries["开始时间 (HH:MM)"].get(),
                "end_time": self.entries["结束时间 (HH:MM)"].get(),
                "course_type": self.entries["课程性质"].get(),
                "grade_level": self.entries["年级段"].get(),
                "is_trial": bool(int(self.entries["是否试听 (0/1)"].get())),
                "students": [s.strip() for s in self.entries["学生（用逗号分隔）"].get().split(",") if s.strip()],
                "subject": self.entries["科目"].get(),
                "location": self.entries["地点"].get(),
                "notes": self.entries["备注"].get(),
            }
            if not payload["title"]:
                raise ValueError("课程名称不能为空")
            dt.date.fromisoformat(payload["course_date"])
            dt.time.fromisoformat(payload["start_time"])
            dt.time.fromisoformat(payload["end_time"])
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("错误", f"输入有误: {exc}")
            return

        if self.on_save:
            self.on_save(payload)
        self.destroy()


class WeekCanvas(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.blocks = {}

    def render(self, week_start: dt.date, courses):
        self.delete("all")
        self.blocks.clear()
        # timeline
        for hour in range(7, 23):
            y = (hour * 60 - START_MINUTES) * PIXELS_PER_MIN
            self.create_line(60, y, WINDOW_WIDTH - 40, y, fill="#e5e5e5")
            self.create_text(35, y, text=f"{hour:02d}:00", anchor=tk.E, fill="#666")

        day_width = (WINDOW_WIDTH - 120) / 7
        for idx in range(7):
            x = 80 + idx * day_width
            self.create_line(x, 0, x, (END_MINUTES - START_MINUTES) * PIXELS_PER_MIN, fill="#ddd")
            date = week_start + dt.timedelta(days=idx)
            self.create_text(x + day_width / 2, 15, text=date.strftime("%m.%d 周%w"), font=("Microsoft YaHei", 10, "bold"))

        for course in courses:
            day_idx = (course.course_date - week_start).days
            if day_idx < 0 or day_idx > 6:
                continue
            x0 = 80 + day_idx * day_width + 4
            x1 = x0 + day_width - 8
            start_minutes = course.start_time.hour * 60 + course.start_time.minute
            end_minutes = course.end_time.hour * 60 + course.end_time.minute
            y0 = (start_minutes - START_MINUTES) * PIXELS_PER_MIN
            y1 = (end_minutes - START_MINUTES) * PIXELS_PER_MIN
            color = GRADE_COLORS.get(course.grade_level, "#dbeafe")
            block = self.create_rectangle(x0, y0, x1, y1, fill=color, outline="#4b5563")
            label = f"{course.title}\n{course.start_time.strftime('%H:%M')} - {course.end_time.strftime('%H:%M')}\n{course.grade_level} {course.course_type}\n学生: {', '.join(course.students)}"
            self.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=label, width=day_width - 10, font=("Microsoft YaHei", 9))
            self.blocks[block] = course.id

    def course_id_from_event(self, event):
        item = self.find_closest(event.x, event.y)
        if not item:
            return None
        return self.blocks.get(item[0])


class TutorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tutor Master")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        database.initialize()
        database.sample_seed()
        self.courses = self._load_courses()
        self.week_start = self._current_week_start()
        self.month = find_course_month(dt.date.today())
        self.mode = "week"
        self._build()

    def _build(self):
        top = tk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(top, text="添加课程 (+)", command=self.add_course_dialog).pack(side=tk.LEFT, padx=8, pady=6)
        self.switch_btn = ttk.Button(top, text="切换到本月课程表", command=self.toggle_mode)
        self.switch_btn.pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="上一周", command=self.prev_week).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="下一周", command=self.next_week).pack(side=tk.LEFT, padx=4)

        self.content = tk.Frame(self)
        self.content.pack(fill=tk.BOTH, expand=True)
        self.week_canvas = WeekCanvas(self.content, bg="white", scrollregion=(0, 0, WINDOW_WIDTH, (END_MINUTES - START_MINUTES) * PIXELS_PER_MIN))
        self.week_canvas.pack(fill=tk.BOTH, expand=True)
        self.week_canvas.bind("<Double-1>", self._on_double_click)

        self.month_frame = tk.Frame(self.content)
        self.month_summary = tk.Label(self.month_frame, text="", anchor=tk.W, justify=tk.LEFT, font=("Microsoft YaHei", 11))
        self.month_summary.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)
        self.month_tree = ttk.Treeview(self.month_frame, columns=("week", "count", "hours"), show="headings")
        self.month_tree.heading("week", text="周范围")
        self.month_tree.heading("count", text="课程数量")
        self.month_tree.heading("hours", text="课时")
        self.month_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.refresh_view()

    def _current_week_start(self):
        today = dt.date.today()
        return today - dt.timedelta(days=today.weekday())

    def _load_courses(self):
        rows = list_courses()
        courses = []
        for row in rows:
            courses.append(
                Course(
                    id=row["id"],
                    title=row["title"],
                    course_date=dt.date.fromisoformat(row["course_date"]),
                    start_time=dt.time.fromisoformat(row["start_time"]),
                    end_time=dt.time.fromisoformat(row["end_time"]),
                    course_type=row["course_type"],
                    grade_level=row["grade_level"],
                    is_trial=bool(row["is_trial"]),
                    students=[s.strip() for s in row["students"].split(",") if s.strip()],
                    notes=row["notes"],
                    location=row["location"],
                    subject=row["subject"],
                )
            )
        return courses

    def refresh_view(self):
        self.courses = self._load_courses()
        if self.mode == "week":
            self.switch_btn.configure(text="切换到本月课程表")
            self.week_canvas.pack(fill=tk.BOTH, expand=True)
            self.month_frame.pack_forget()
            courses = [c for c in self.courses if self.week_start <= c.course_date <= self.week_start + dt.timedelta(days=6)]
            self.week_canvas.config(scrollregion=(0, 0, WINDOW_WIDTH, (END_MINUTES - START_MINUTES) * PIXELS_PER_MIN))
            self.week_canvas.render(self.week_start, courses)
        else:
            self.switch_btn.configure(text="返回本周")
            self.week_canvas.pack_forget()
            self.month_frame.pack(fill=tk.BOTH, expand=True)
            self.render_month()

    def render_month(self):
        self.month = find_course_month(dt.date.today())
        self.month_tree.delete(*self.month_tree.get_children())
        weeks = group_by_week(self.month.start_date, self.month.end_date)
        month_courses = list(filter_courses_for_month(self.courses, self.month.start_date, self.month.end_date))
        for week_start, week_end in weeks:
            week_courses = [c for c in month_courses if week_start <= c.course_date <= week_end]
            total_hours = sum(c.course_hours for c in week_courses)
            self.month_tree.insert("", tk.END, values=(
                f"{week_start:%m.%d}-{week_end:%m.%d}",
                len(week_courses),
                f"{total_hours:.1f}",
            ))
        salary = calculate_salary(month_courses, self.month.month_name, is_holiday=self.month.is_holiday)
        summary = (
            f"{self.month.month_name} (季度Q{self.month.quarter}) \n"
            f"课程月范围: {self.month.start_date} 至 {self.month.end_date}\n"
            f"月份类型: {'寒暑假' if self.month.is_holiday else '常规月'}; 义务课时: {salary.duty_hours} 节\n"
            f"总课时: {salary.payable_hours:.1f}; 课时费: ￥{salary.hourly_income:.2f}; \n"
            f"薪资 = 底薪5000 + 课时费 + 续费奖({salary.renew_bonus}) + 课时奖({salary.class_bonus}) - 扣罚({salary.penalty}) = ￥{salary.total:.2f}"
        )
        self.month_summary.configure(text=summary)

    def toggle_mode(self):
        self.mode = "month" if self.mode == "week" else "week"
        self.refresh_view()

    def prev_week(self):
        self.week_start -= dt.timedelta(days=7)
        if self.mode == "week":
            self.refresh_view()

    def next_week(self):
        self.week_start += dt.timedelta(days=7)
        if self.mode == "week":
            self.refresh_view()

    def add_course_dialog(self):
        CourseDialog(self, "新增课程", on_save=self._create_course)

    def _create_course(self, payload):
        add_course(**payload)
        self.refresh_view()

    def _on_double_click(self, event):
        course_id = self.week_canvas.course_id_from_event(event)
        if not course_id:
            return
        row = get_course(course_id)
        if not row:
            return
        initial = dict(row)
        dlg = CourseDialog(self, "编辑 / 删除课程", initial=initial, on_save=lambda p: self._update_course(course_id, p))
        dlg.transient(self)
        dlg.grab_set()
        self.bind("<Delete>", lambda _e: self._confirm_delete(course_id))

    def _update_course(self, course_id: int, payload):
        update_course(course_id, **payload)
        self.refresh_view()

    def _confirm_delete(self, course_id: int):
        if messagebox.askyesno("删除", "确认删除这节课吗？"):
            delete_course(course_id)
            self.refresh_view()


if __name__ == "__main__":
    app = TutorApp()
    app.mainloop()
