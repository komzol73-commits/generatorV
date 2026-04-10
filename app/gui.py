"""Основной модуль графического интерфейса.

Здесь находится окно Tkinter, обработчики действий пользователя, запуск
генератора в фоне и обновление превью/лога. Это центр всей GUI-логики.
"""

from __future__ import annotations

import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, W, X, Y, BooleanVar, IntVar, StringVar, Tk, filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .gui_support import (
    append_log,
    compute_dimension_summary,
    configure_ttk_styles,
    format_command,
    load_preview_image,
    open_in_system,
    resolve_ui_font,
)
from .runner import DEFAULT_OUTPUT_DIR, build_command, build_subprocess_env


class CrossStitchApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Генератор 2")
        self.root.geometry("980x760")
        self.root.minsize(900, 680)
        self.ui_font = resolve_ui_font(root)

        self.image_path = StringVar()
        self.output_name = StringVar(value="pattern_test")
        self.output_dir = StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.width = IntVar(value=180)
        self.colors = IntVar(value=30)
        self.aida = IntVar(value=14)
        self.title = StringVar(value="")
        self.use_blends = BooleanVar(value=False)
        self.no_oxs = BooleanVar(value=False)

        self.size_summary = StringVar(value="180 крестиков по ширине")
        self.fabric_summary = StringVar(value="Размер на канве 14 ct: 32.7 см по ширине")

        self._source_preview = None
        self._result_preview = None
        self._build_thread: threading.Thread | None = None
        self._process: subprocess.Popen[str] | None = None

        self._build_ui()
        self.width.trace_add('write', self._refresh_dimension_summary)
        self.aida.trace_add('write', self._refresh_dimension_summary)
        self._refresh_dimension_summary()

    def _build_ui(self) -> None:
        configure_ttk_styles(self.root, self.ui_font)

        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill=BOTH, expand=True)

        header = tk.Frame(outer, bg="#5c7f4f", height=64)
        header.pack(fill=X, pady=(0, 12))
        header.pack_propagate(False)
        tk.Label(header, text="Генератор 2", bg="#5c7f4f", fg="white", font=(self.ui_font, 18, 'bold')).pack(anchor='w', padx=16, pady=(10, 0))
        tk.Label(header, text="Русский интерфейс и PDF-оформление", bg="#5c7f4f", fg="#e8f2df", font=(self.ui_font, 10)).pack(anchor='w', padx=16, pady=(0, 10))

        top = ttk.Frame(outer)
        top.pack(fill=X)
        left = ttk.Frame(top)
        left.pack(side=LEFT, fill=BOTH, expand=True)
        right = ttk.Frame(top)
        right.pack(side=RIGHT, fill=Y, padx=(18, 0))

        self._build_form(left)
        self._build_previews(right)
        self._build_log(outer)

    def _build_form(self, parent: ttk.Frame) -> None:
        file_box = ttk.LabelFrame(parent, text="Файлы", padding=10)
        file_box.pack(fill=X)
        ttk.Label(file_box, text="Изображение").grid(row=0, column=0, sticky=W, pady=4)
        ttk.Entry(file_box, textvariable=self.image_path, width=62).grid(row=0, column=1, sticky='ew', padx=8, pady=4)
        ttk.Button(file_box, text="Выбрать", command=self._choose_image).grid(row=0, column=2, pady=4)
        ttk.Label(file_box, text="Имя проекта").grid(row=1, column=0, sticky=W, pady=4)
        ttk.Entry(file_box, textvariable=self.output_name, width=32).grid(row=1, column=1, sticky=W, padx=8, pady=4)
        ttk.Label(file_box, text="Папка вывода").grid(row=2, column=0, sticky=W, pady=4)
        ttk.Entry(file_box, textvariable=self.output_dir, width=62).grid(row=2, column=1, sticky='ew', padx=8, pady=4)
        ttk.Button(file_box, text="Папка", command=self._choose_output_dir).grid(row=2, column=2, pady=4)
        file_box.columnconfigure(1, weight=1)

        settings_box = ttk.LabelFrame(parent, text="Параметры", padding=10)
        settings_box.pack(fill=X, pady=(12, 0))
        ttk.Label(settings_box, text="Ширина").grid(row=0, column=0, sticky=W, pady=4)
        ttk.Spinbox(settings_box, from_=20, to=400, textvariable=self.width, width=8).grid(row=0, column=1, sticky=W, padx=(8, 18), pady=4)
        ttk.Label(settings_box, text="Цветов").grid(row=0, column=2, sticky=W, pady=4)
        ttk.Spinbox(settings_box, from_=2, to=80, textvariable=self.colors, width=8).grid(row=0, column=3, sticky=W, padx=(8, 18), pady=4)
        ttk.Label(settings_box, text="Aida").grid(row=0, column=4, sticky=W, pady=4)
        ttk.Spinbox(settings_box, from_=11, to=20, textvariable=self.aida, width=8).grid(row=0, column=5, sticky=W, padx=(8, 0), pady=4)
        ttk.Label(settings_box, text="Заголовок PDF").grid(row=1, column=0, sticky=W, pady=4)
        ttk.Entry(settings_box, textvariable=self.title, width=42).grid(row=1, column=1, columnspan=5, sticky='ew', padx=(8, 0), pady=4)
        ttk.Checkbutton(settings_box, text="Использовать бленды", variable=self.use_blends).grid(row=2, column=0, columnspan=2, sticky=W, pady=4)
        ttk.Checkbutton(settings_box, text="Без OXS", variable=self.no_oxs).grid(row=2, column=2, columnspan=2, sticky=W, pady=4)
        ttk.Label(settings_box, textvariable=self.size_summary).grid(row=3, column=0, columnspan=3, sticky=W, pady=(8, 0))
        ttk.Label(settings_box, textvariable=self.fabric_summary).grid(row=3, column=3, columnspan=3, sticky=W, pady=(8, 0))

        actions = ttk.Frame(parent)
        actions.pack(fill=X, pady=(14, 0))
        self.build_button = ttk.Button(actions, text="Собрать схему", command=self._start_build)
        self.build_button.pack(side=LEFT)
        ttk.Button(actions, text="Открыть папку", command=self._open_output_dir).pack(side=LEFT, padx=(10, 0))
        ttk.Button(actions, text="Открыть PDF", command=self._open_latest_pdf).pack(side=LEFT, padx=(10, 0))

    def _build_previews(self, parent: ttk.Frame) -> None:
        source_box = ttk.LabelFrame(parent, text="Исходник", padding=8)
        source_box.pack(fill=BOTH, expand=True)
        self.source_label = ttk.Label(source_box, text="Нет изображения", anchor='center')
        self.source_label.pack(fill=BOTH, expand=True)

        result_box = ttk.LabelFrame(parent, text="Preview после конвертации", padding=8)
        result_box.pack(fill=BOTH, expand=True, pady=(12, 0))
        self.result_label = ttk.Label(result_box, text="Пока пусто", anchor='center')
        self.result_label.pack(fill=BOTH, expand=True)

    def _build_log(self, parent: ttk.Frame) -> None:
        log_box = ttk.LabelFrame(parent, text="Лог", padding=8)
        log_box.pack(fill=BOTH, expand=True, pady=(14, 0))
        self.log = ScrolledText(log_box, height=14, wrap='word', font=(self.ui_font, 10))
        self.log.pack(fill=BOTH, expand=True)
        self.log.configure(state='disabled')
        self._append_log("Готово к тестированию.")

    def _choose_image(self) -> None:
        selected = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")],
        )
        if not selected:
            return
        selected_path = Path(selected)
        self.image_path.set(selected)
        if not self.title.get().strip():
            self.title.set(selected_path.stem)
        if not self.output_name.get().strip() or self.output_name.get() == 'pattern_test':
            self.output_name.set(selected_path.stem)
        self._load_preview(selected_path, target='source')

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Папка для результатов", initialdir=self.output_dir.get())
        if selected:
            self.output_dir.set(selected)

    def _load_preview(self, path: Path, target: str) -> None:
        tk_image = load_preview_image(path)
        if tk_image is None:
            return
        label = self.source_label if target == 'source' else self.result_label
        label.configure(image=tk_image, text='')
        if target == 'source':
            self._source_preview = tk_image
        else:
            self._result_preview = tk_image

    def _append_log(self, text: str) -> None:
        append_log(self.log, text)

    def _set_running(self, running: bool) -> None:
        self.build_button.configure(state='disabled' if running else 'normal')

    def _refresh_dimension_summary(self, *_args) -> None:
        size_text, fabric_text = compute_dimension_summary(self.width.get(), self.aida.get())
        self.size_summary.set(size_text)
        self.fabric_summary.set(fabric_text)

    def _validate(self):
        if not self.image_path.get().strip():
            messagebox.showerror("Нет файла", "Выберите изображение.")
            return None
        try:
            return build_command(
                image=self.image_path.get().strip(),
                output_name=self.output_name.get().strip(),
                output_dir=self.output_dir.get().strip(),
                width=self.width.get(),
                colors=self.colors.get(),
                aida=self.aida.get(),
                title=self.title.get().strip(),
                use_blends=self.use_blends.get(),
                no_oxs=self.no_oxs.get(),
            )
        except SystemExit as exc:
            messagebox.showerror("Ошибка", str(exc))
            return None

    def _start_build(self) -> None:
        if self._build_thread and self._build_thread.is_alive():
            messagebox.showinfo("Сборка идет", "Дождитесь окончания текущей сборки.")
            return
        prepared = self._validate()
        if not prepared:
            return
        command, output_pdf = prepared
        self.log.configure(state='normal')
        self.log.delete('1.0', END)
        self.log.configure(state='disabled')
        self._append_log(f"Старт: {Path(self.image_path.get()).name}")
        self._append_log(format_command(command))
        self._set_running(True)
        self._build_thread = threading.Thread(target=self._run_build, args=(command, output_pdf), daemon=True)
        self._build_thread.start()

    def _run_build(self, command: list[str], output_pdf: Path) -> None:
        try:
            self._process = subprocess.Popen(
                command,
                cwd=Path(__file__).resolve().parent.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=build_subprocess_env(),
            )
            assert self._process.stdout is not None
            for line in self._process.stdout:
                self.root.after(0, self._append_log, line.rstrip())
            code = self._process.wait()
            if code != 0:
                self.root.after(0, self._append_log, f"Ошибка. Код: {code}")
                self.root.after(0, messagebox.showerror, "Ошибка", "Генерация завершилась с ошибкой. Смотри лог.")
                return
            preview_path = output_pdf.with_name(f"{output_pdf.stem}_preview.png")
            if preview_path.exists():
                self.root.after(0, lambda p=preview_path: self._load_preview(p, target='result'))
            self.root.after(0, self._append_log, f"Сохранено: {output_pdf}")
            self.root.after(0, messagebox.showinfo, "Готово", f"PDF сохранен:\n{output_pdf}")
        except Exception as exc:
            self.root.after(0, self._append_log, str(exc))
            self.root.after(0, messagebox.showerror, "Ошибка", str(exc))
        finally:
            self._process = None
            self.root.after(0, self._set_running, False)

    def _open_output_dir(self) -> None:
        path = Path(self.output_dir.get().strip() or DEFAULT_OUTPUT_DIR)
        path.mkdir(parents=True, exist_ok=True)
        open_in_system(path)

    def _open_latest_pdf(self) -> None:
        pdf_path = Path(self.output_dir.get().strip() or DEFAULT_OUTPUT_DIR) / f"{self.output_name.get().strip() or 'pattern_test'}.pdf"
        if not pdf_path.exists():
            messagebox.showinfo("PDF не найден", "Сначала соберите схему с форматом PDF.")
            return
        open_in_system(pdf_path)


def main() -> int:
    root = Tk()
    CrossStitchApp(root)
    root.mainloop()
    return 0
