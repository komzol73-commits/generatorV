# =============================================================================
#  gui_app.py
# -----------------------------------------------------------------------------
#  Графический интерфейс (Tkinter) для генератора схем вышивки крестиком.
#
#  Что делает приложение:
#    * позволяет выбрать исходное изображение, папку и имя проекта;
#    * настраивает параметры: ширину в крестиках, палитру, каунт канвы;
#    * запускает дочерний процесс generate_pattern.py в отдельном потоке,
#      чтобы интерфейс не "замораживался" во время обработки;
#    * показывает превью исходника и результата, а также лог работы;
#    * открывает папку с результатами и последний PDF прямо из окна.
#
#  Структура файла:
#    1. Импорты
#    2. Класс CrossStitchApp
#       2.1 Конструктор и переменные состояния
#       2.2 Настройка шрифтов/стилей
#       2.3 Построение интерфейса (_build_ui и помощники)
#       2.4 Обработчики пользовательских действий
#       2.5 Работа с превью и логом
#       2.6 Валидация и запуск сборки схемы
#       2.7 Фоновый поток генерации
#       2.8 Открытие папки и PDF-файла
#    3. Функция main() и точка входа
# =============================================================================

from __future__ import annotations  # отложенные аннотации типов

# -----------------------------------------------------------------------------
# 1. ИМПОРТЫ
# -----------------------------------------------------------------------------
import os           # для os.startfile() — открыть папку/файл через ассоциации Windows
import subprocess   # запуск дочернего процесса с генератором
import threading    # фоновый поток, чтобы GUI не зависал во время генерации
import tkinter as tk                # базовый модуль Tkinter
import tkinter.font as tkfont       # работа со шрифтами (проверка доступности Inter)
from pathlib import Path            # кроссплатформенные пути
from tkinter import (
    BOTH, END, LEFT, RIGHT, W, X, Y,  # константы позиционирования/ориентации
    BooleanVar, IntVar, StringVar,     # переменные-обёртки Tk (биндятся к виджетам)
    Tk,                                 # основной класс окна
    filedialog, messagebox, ttk,        # стандартные диалоги и современные виджеты
)
from tkinter.scrolledtext import ScrolledText  # многострочное текстовое поле со скроллом

from PIL import Image, ImageTk  # Pillow: загрузка/изменение размеров изображений для предпросмотра

# Импортируем функции-помощники из соседнего модуля-обёртки.
# DEFAULT_OUTPUT_DIR   — папка по умолчанию для результатов.
# build_command        — собирает список аргументов запуска generate_pattern.py.
# build_subprocess_env — готовит окружение с UTF-8 для дочернего процесса.
from run_generator import DEFAULT_OUTPUT_DIR, build_command, build_subprocess_env


# =============================================================================
# 2. КЛАСС CrossStitchApp — основное окно приложения
# =============================================================================
class CrossStitchApp:
    # -------------------------------------------------------------------------
    # 2.1 Конструктор и переменные состояния
    # -------------------------------------------------------------------------
    def __init__(self, root: Tk) -> None:
        """Инициализация главного окна и всех переменных, привязанных к виджетам."""
        # Сохраняем ссылку на корневое окно Tk — оно понадобится для after(), стилей и т.д.
        self.root = root
        self.root.title("Генератор 2")          # заголовок окна
        self.root.geometry("980x760")            # стартовый размер окна
        self.root.minsize(900, 680)              # минимальный размер — чтобы виджеты не ломались
        self.ui_font = "Inter"                   # желаемый шрифт (подменяется на Segoe UI, если Inter не установлен)

        # --- Переменные, привязанные к полям формы (двусторонняя связь с виджетами) ---
        self.image_path = StringVar()                                  # путь к выбранному изображению
        self.output_name = StringVar(value="pattern_test")             # имя проекта (база имён выходных файлов)
        self.output_dir = StringVar(value=str(DEFAULT_OUTPUT_DIR))     # папка вывода
        self.width = IntVar(value=180)                                 # ширина схемы в крестиках
        self.colors = IntVar(value=30)                                 # число цветов палитры
        self.aida = IntVar(value=14)                                   # каунт канвы (ct)
        self.title = StringVar(value="")                               # заголовок титульного листа PDF
        self.use_blends = BooleanVar(value=False)                      # использовать бленды (смешивание цветов)
        self.no_oxs = BooleanVar(value=False)                          # не экспортировать OXS-файл

        # --- Текстовые строки-подсказки, которые автоматически обновляются при изменении width/aida ---
        self.size_summary = StringVar(value="180 крестиков по ширине")
        self.fabric_summary = StringVar(value="Размер на канве 14 ct: 32.7 см по ширине")

        # --- Внутреннее состояние (кеш изображений и ссылка на фоновый поток/процесс) ---
        # PhotoImage нельзя складывать в локальные переменные — их съест сборщик мусора
        # и картинки исчезнут. Поэтому храним как атрибуты объекта.
        self._source_preview: ImageTk.PhotoImage | None = None   # превью исходного изображения
        self._result_preview: ImageTk.PhotoImage | None = None   # превью итоговой схемы
        self._build_thread: threading.Thread | None = None       # фоновый поток сборки
        self._process: subprocess.Popen[str] | None = None       # дочерний процесс генератора

        # --- Строим интерфейс и подключаем автоматическое обновление подсказок о размере ---
        self._build_ui()
        # trace_add("write", ...) вызывает коллбэк при любом изменении переменной.
        self.width.trace_add("write", self._refresh_dimension_summary)
        self.aida.trace_add("write", self._refresh_dimension_summary)
        # Выставляем актуальные подсказки при старте.
        self._refresh_dimension_summary()

    # -------------------------------------------------------------------------
    # 2.2 Настройка шрифтов и стилей ttk
    # -------------------------------------------------------------------------
    def _apply_fonts(self) -> None:
        """Пытается использовать шрифт Inter; если его нет — откатывается на Segoe UI."""
        try:
            # families() может кинуть TclError в нестандартных окружениях — страхуемся.
            available = set(tkfont.families(self.root))
        except tk.TclError:
            available = set()

        if "Inter" not in available:
            self.ui_font = "Segoe UI"

        # ttk.Style управляет стилями современных виджетов (кнопок, полей, чекбоксов).
        style = ttk.Style(self.root)
        # "." — базовый стиль, от которого наследуются все остальные.
        style.configure(".", font=(self.ui_font, 10))
        style.configure("TButton", font=(self.ui_font, 10))
        style.configure("TLabel", font=(self.ui_font, 10))
        # Заголовки LabelFrame делаем жирными для лучшей читаемости.
        style.configure("TLabelframe.Label", font=(self.ui_font, 10, "bold"))
        style.configure("TCheckbutton", font=(self.ui_font, 10))

    # -------------------------------------------------------------------------
    # 2.3 Построение интерфейса
    # -------------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Корневой метод построения UI. Собирает хедер, левую форму, правые превью и лог."""
        self._apply_fonts()

        # Внешний контейнер с внутренними отступами — основа всей раскладки.
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill=BOTH, expand=True)

        # --- Верхний цветной хедер с названием приложения ---
        # Фон через tk.Frame (а не ttk), чтобы можно было задать цвет напрямую.
        header = tk.Frame(outer, bg="#5c7f4f", height=64)
        header.pack(fill=X, pady=(0, 12))
        # pack_propagate(False) фиксирует высоту фрейма: иначе он "схлопнется" под содержимое.
        header.pack_propagate(False)
        # Главный заголовок-название.
        tk.Label(
            header, text="Генератор 2", bg="#5c7f4f", fg="white",
            font=(self.ui_font, 18, "bold"),
        ).pack(anchor="w", padx=16, pady=(10, 0))
        # Подзаголовок под именем.
        tk.Label(
            header, text="Русский интерфейс и PDF-оформление",
            bg="#5c7f4f", fg="#e8f2df", font=(self.ui_font, 10),
        ).pack(anchor="w", padx=16, pady=(0, 10))

        # --- Основная область, разделённая на левую (форма) и правую (превью) части ---
        top = ttk.Frame(outer)
        top.pack(fill=X)

        left = ttk.Frame(top)
        left.pack(side=LEFT, fill=BOTH, expand=True)

        right = ttk.Frame(top)
        right.pack(side=RIGHT, fill=Y, padx=(18, 0))

        # Делегируем построение каждого блока в отдельные методы — так проще читать.
        self._build_form(left)      # левая часть: поля и кнопки
        self._build_previews(right) # правая часть: превью
        self._build_log(outer)      # нижняя часть: лог выполнения

    def _build_form(self, parent: ttk.Frame) -> None:
        """Левая колонка: два блока с настройками и панель действий."""
        # ----- Блок "Файлы": путь к изображению, имя проекта, папка вывода -----
        file_box = ttk.LabelFrame(parent, text="Файлы", padding=10)
        file_box.pack(fill=X)

        # Строка 0: выбор изображения.
        ttk.Label(file_box, text="Изображение").grid(row=0, column=0, sticky=W, pady=4)
        ttk.Entry(file_box, textvariable=self.image_path, width=62).grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(file_box, text="Выбрать", command=self._choose_image).grid(row=0, column=2, pady=4)

        # Строка 1: базовое имя проекта (используется для названий выходных файлов).
        ttk.Label(file_box, text="Имя проекта").grid(row=1, column=0, sticky=W, pady=4)
        ttk.Entry(file_box, textvariable=self.output_name, width=32).grid(row=1, column=1, sticky=W, padx=8, pady=4)

        # Строка 2: путь к папке вывода + кнопка диалогового выбора.
        ttk.Label(file_box, text="Папка вывода").grid(row=2, column=0, sticky=W, pady=4)
        ttk.Entry(file_box, textvariable=self.output_dir, width=62).grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(file_box, text="Папка", command=self._choose_output_dir).grid(row=2, column=2, pady=4)
        # Столбец 1 (ввод) должен растягиваться при изменении ширины окна.
        file_box.columnconfigure(1, weight=1)

        # ----- Блок "Параметры": числовые настройки схемы -----
        settings_box = ttk.LabelFrame(parent, text="Параметры", padding=10)
        settings_box.pack(fill=X, pady=(12, 0))

        # Строка 0: три Spinbox-поля в ряд — Ширина, Цветов, Aida.
        ttk.Label(settings_box, text="Ширина").grid(row=0, column=0, sticky=W, pady=4)
        ttk.Spinbox(settings_box, from_=20, to=400, textvariable=self.width, width=8).grid(
            row=0, column=1, sticky=W, padx=(8, 18), pady=4
        )
        ttk.Label(settings_box, text="Цветов").grid(row=0, column=2, sticky=W, pady=4)
        ttk.Spinbox(settings_box, from_=2, to=80, textvariable=self.colors, width=8).grid(
            row=0, column=3, sticky=W, padx=(8, 18), pady=4
        )
        ttk.Label(settings_box, text="Aida").grid(row=0, column=4, sticky=W, pady=4)
        ttk.Spinbox(settings_box, from_=11, to=20, textvariable=self.aida, width=8).grid(
            row=0, column=5, sticky=W, padx=(8, 0), pady=4
        )

        # Строка 1: поле для заголовка PDF — растягивается на несколько колонок.
        ttk.Label(settings_box, text="Заголовок PDF").grid(row=1, column=0, sticky=W, pady=4)
        ttk.Entry(settings_box, textvariable=self.title, width=42).grid(
            row=1, column=1, columnspan=5, sticky="ew", padx=(8, 0), pady=4
        )

        # Строка 2: флаги-переключатели — использовать бленды и отключить OXS.
        ttk.Checkbutton(settings_box, text="Использовать бленды", variable=self.use_blends).grid(
            row=2, column=0, columnspan=2, sticky=W, pady=4
        )
        ttk.Checkbutton(settings_box, text="Без OXS", variable=self.no_oxs).grid(
            row=2, column=2, columnspan=2, sticky=W, pady=4
        )

        # Строка 3: автоматически обновляемые подписи с расчётом размеров в см.
        ttk.Label(settings_box, textvariable=self.size_summary).grid(
            row=3, column=0, columnspan=3, sticky=W, pady=(8, 0)
        )
        ttk.Label(settings_box, textvariable=self.fabric_summary).grid(
            row=3, column=3, columnspan=3, sticky=W, pady=(8, 0)
        )

        # ----- Панель действий: основные кнопки -----
        actions = ttk.Frame(parent)
        actions.pack(fill=X, pady=(14, 0))
        # Главная кнопка — сохранена как атрибут, чтобы её можно было блокировать во время сборки.
        self.build_button = ttk.Button(actions, text="Собрать схему", command=self._start_build)
        self.build_button.pack(side=LEFT)
        ttk.Button(actions, text="Открыть папку", command=self._open_output_dir).pack(side=LEFT, padx=(10, 0))
        ttk.Button(actions, text="Открыть PDF", command=self._open_latest_pdf).pack(side=LEFT, padx=(10, 0))

    def _build_previews(self, parent: ttk.Frame) -> None:
        """Правая колонка: два блока с предпросмотром — исходник и результат."""
        # Блок с исходным изображением.
        source_box = ttk.LabelFrame(parent, text="Исходник", padding=8)
        source_box.pack(fill=BOTH, expand=True)
        # Изначально — просто текст "Нет изображения"; картинка появится после выбора файла.
        self.source_label = ttk.Label(source_box, text="Нет изображения", anchor="center")
        self.source_label.pack(fill=BOTH, expand=True)

        # Блок с результатом (появляется после генерации схемы).
        result_box = ttk.LabelFrame(parent, text="Preview после конвертации", padding=8)
        result_box.pack(fill=BOTH, expand=True, pady=(12, 0))
        self.result_label = ttk.Label(result_box, text="Пока пусто", anchor="center")
        self.result_label.pack(fill=BOTH, expand=True)

    def _build_log(self, parent: ttk.Frame) -> None:
        """Нижний блок: текстовый лог с вертикальной прокруткой."""
        log_box = ttk.LabelFrame(parent, text="Лог", padding=8)
        log_box.pack(fill=BOTH, expand=True, pady=(14, 0))
        # wrap="word" — перенос по словам, а не по символам.
        self.log = ScrolledText(log_box, height=14, wrap="word", font=(self.ui_font, 10))
        self.log.pack(fill=BOTH, expand=True)
        # state="disabled" — пользователь не может редактировать лог руками.
        # Мы временно переключаем в "normal" при дозаписи.
        self.log.configure(state="disabled")
        self._append_log("Готово к тестированию.")

    # -------------------------------------------------------------------------
    # 2.4 Обработчики пользовательских действий (выбор файла/папки)
    # -------------------------------------------------------------------------
    def _choose_image(self) -> None:
        """Открывает диалог выбора изображения и заполняет связанные поля."""
        selected = filedialog.askopenfilename(
            title="Выберите изображение",
            # Фильтр расширений — удобнее пользователю видеть только картинки.
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")],
        )
        # Если пользователь нажал "Отмена" — ничего не делаем.
        if not selected:
            return

        selected_path = Path(selected)
        self.image_path.set(selected)

        # Автозаполнение заголовка и имени проекта именем файла (без расширения),
        # если пользователь сам ничего ещё не ввёл.
        if not self.title.get().strip():
            self.title.set(selected_path.stem)
        if not self.output_name.get().strip() or self.output_name.get() == "pattern_test":
            self.output_name.set(selected_path.stem)

        # Сразу показываем превью выбранной картинки в правой части окна.
        self._load_preview(selected_path, target="source")

    def _choose_output_dir(self) -> None:
        """Открывает диалог выбора папки для сохранения результатов."""
        selected = filedialog.askdirectory(
            title="Папка для результатов",
            initialdir=self.output_dir.get(),  # открываемся в текущем пути
        )
        if selected:
            self.output_dir.set(selected)

    # -------------------------------------------------------------------------
    # 2.5 Работа с превью и логом
    # -------------------------------------------------------------------------
    def _load_preview(self, path: Path, target: str) -> None:
        """Загружает изображение, уменьшает до 280×280 и вставляет в нужный Label.

        Parameters
        ----------
        path : Path
            Путь к файлу картинки (PNG/JPG/...).
        target : str
            "source" — превью исходника, иначе — превью результата.
        """
        if not path.exists():
            return

        # convert('RGB') — нормализуем цветовую модель (на случай PNG с альфа-каналом).
        image = Image.open(path).convert("RGB")
        # thumbnail меняет размер "на месте", сохраняя пропорции, и НЕ увеличивает маленькие картинки.
        image.thumbnail((280, 280))
        tk_image = ImageTk.PhotoImage(image)

        label = self.source_label if target == "source" else self.result_label
        # Устанавливаем картинку и одновременно убираем текст-заглушку.
        label.configure(image=tk_image, text="")

        # Сохраняем ссылку на PhotoImage в атрибуте, иначе GC её уничтожит.
        if target == "source":
            self._source_preview = tk_image
        else:
            self._result_preview = tk_image

    def _append_log(self, text: str) -> None:
        """Дописывает строку в лог и прокручивает его к концу."""
        # Временно разрешаем запись, вставляем строку, возвращаем disabled.
        self.log.configure(state="normal")
        self.log.insert(END, text + "\n")
        self.log.see(END)  # автоскролл к новой строке
        self.log.configure(state="disabled")

    def _set_running(self, running: bool) -> None:
        """Блокирует/разблокирует кнопку "Собрать схему" во время фоновой сборки."""
        self.build_button.configure(state="disabled" if running else "normal")

    def _refresh_dimension_summary(self, *_args) -> None:
        """Пересчитывает подписи о размере схемы (в крестиках и в сантиметрах)."""
        # max(..., 1) — защита от нуля и отрицательных значений, которые могут
        # возникнуть при вводе вручную в Spinbox.
        width = max(1, self.width.get())
        aida = max(1, self.aida.get())
        # Перевод крестиков в сантиметры: ширина / каунт_на_дюйм * 2.54.
        width_cm = round(width / aida * 2.54, 1)
        self.size_summary.set(f"{width} крестиков по ширине")
        self.fabric_summary.set(f"Размер на канве {aida} ct: {width_cm} см по ширине")

    # -------------------------------------------------------------------------
    # 2.6 Валидация и запуск сборки схемы
    # -------------------------------------------------------------------------
    def _validate(self):
        """Проверяет корректность ввода и формирует команду запуска генератора.

        Возвращает результат build_command() или None при ошибке. При ошибке
        показывает пользователю соответствующее сообщение.
        """
        # Минимальная проверка: без картинки запускать бессмысленно.
        if not self.image_path.get().strip():
            messagebox.showerror("Нет файла", "Выберите изображение.")
            return None

        try:
            # build_command может кинуть SystemExit, если путь к картинке
            # или скрипту-генератору невалиден. Ловим и показываем в диалоге.
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
        """Нажатие кнопки "Собрать схему": валидация + запуск фонового потока."""
        # Если уже идёт сборка — просто сообщаем об этом и выходим.
        if self._build_thread and self._build_thread.is_alive():
            messagebox.showinfo("Сборка идет", "Дождитесь окончания текущей сборки.")
            return

        # Валидируем поля и собираем команду запуска.
        prepared = self._validate()
        if not prepared:
            return

        command, output_pdf = prepared

        # Очищаем лог перед новым запуском, чтобы не смешивались сообщения.
        self.log.configure(state="normal")
        self.log.delete("1.0", END)
        self.log.configure(state="disabled")

        # Пишем в лог имя исходника и фактическую команду запуска.
        self._append_log(f"Старт: {Path(self.image_path.get()).name}")
        self._append_log(" ".join(f'"{part}"' if " " in part else part for part in command))

        # Блокируем кнопку и запускаем фоновый поток.
        self._set_running(True)
        # daemon=True — поток завершится автоматически при закрытии окна.
        self._build_thread = threading.Thread(
            target=self._run_build, args=(command, output_pdf), daemon=True
        )
        self._build_thread.start()

    # -------------------------------------------------------------------------
    # 2.7 Фоновый поток генерации
    # -------------------------------------------------------------------------
    def _run_build(self, command: list[str], output_pdf: Path) -> None:
        """Запускает дочерний процесс и построчно выводит его stdout в лог.

        Запускается ИЗ ФОНОВОГО ПОТОКА, поэтому все обращения к виджетам
        делаются через self.root.after(0, ...) — этот метод планирует вызов
        в главном GUI-потоке Tk, что единственно безопасно для Tkinter.
        """
        try:
            # Popen запускает процесс и не блокирует поток.
            # stdout=PIPE, stderr=STDOUT — сливаем оба потока в один, чтобы читать последовательно.
            # text=True + encoding="utf-8" — читаем строки сразу в str (а не bytes).
            # errors="replace" — если встретится сломанный байт, подставим "?", а не упадём.
            self._process = subprocess.Popen(
                command,
                cwd=Path(__file__).resolve().parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=build_subprocess_env(),
            )
            # Подсказка тайп-чекеру: stdout точно не None, так как мы передали PIPE.
            assert self._process.stdout is not None

            # Читаем stdout построчно по мере поступления — удобно для live-лога.
            for line in self._process.stdout:
                # after(0, ...) — безопасная передача обновления в GUI-поток.
                self.root.after(0, self._append_log, line.rstrip())

            # Ждём завершения процесса и проверяем код возврата.
            code = self._process.wait()
            if code != 0:
                # Ошибка — сообщаем в лог и диалогом.
                self.root.after(0, self._append_log, f"Ошибка. Код: {code}")
                self.root.after(0, messagebox.showerror, "Ошибка",
                                 "Генерация завершилась с ошибкой. Смотри лог.")
                return

            # Успех: ищем файл превью рядом с PDF и показываем его в окне.
            # Генератор сохраняет превью как "<имя>_preview.png".
            preview_path = output_pdf.with_name(f"{output_pdf.stem}_preview.png")
            if preview_path.exists():
                # lambda p=preview_path — фиксируем значение переменной в замыкании.
                self.root.after(0, lambda p=preview_path: self._load_preview(p, target="result"))
            self.root.after(0, self._append_log, f"Сохранено: {output_pdf}")
            self.root.after(0, messagebox.showinfo, "Готово", f"PDF сохранен:\n{output_pdf}")

        except Exception as exc:
            # Любая неожиданная ошибка (например, не найден интерпретатор) — в лог и диалог.
            self.root.after(0, self._append_log, str(exc))
            self.root.after(0, messagebox.showerror, "Ошибка", str(exc))
        finally:
            # Независимо от исхода — сбрасываем процесс и разблокируем кнопку.
            self._process = None
            self.root.after(0, self._set_running, False)

    # -------------------------------------------------------------------------
    # 2.8 Открытие папки и готового PDF
    # -------------------------------------------------------------------------
    def _open_output_dir(self) -> None:
        """Открывает папку с результатами в Проводнике Windows."""
        # Если поле пустое — используем папку по умолчанию.
        path = Path(self.output_dir.get().strip() or DEFAULT_OUTPUT_DIR)
        # Создаём папку на всякий случай, чтобы os.startfile не упал.
        path.mkdir(parents=True, exist_ok=True)
        # os.startfile доступен только на Windows (nt — это Windows).
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]

    def _open_latest_pdf(self) -> None:
        """Открывает только что собранный PDF (по текущим полям формы)."""
        # Путь = папка вывода + имя проекта + ".pdf".
        pdf_path = (
            Path(self.output_dir.get().strip() or DEFAULT_OUTPUT_DIR)
            / f"{self.output_name.get().strip() or 'pattern_test'}.pdf"
        )
        # Если файла ещё нет — подсказываем сначала собрать схему.
        if not pdf_path.exists():
            messagebox.showinfo("PDF не найден", "Сначала соберите схему с форматом PDF.")
            return
        if os.name == "nt":
            os.startfile(pdf_path)  # type: ignore[attr-defined]


# =============================================================================
# 3. ТОЧКА ВХОДА
# =============================================================================
def main() -> int:
    """Создаёт корневое окно и запускает главный цикл событий Tkinter."""
    root = Tk()
    CrossStitchApp(root)
    # mainloop() блокирует выполнение до закрытия окна — это обычное поведение Tk.
    root.mainloop()
    return 0


# Защитный блок: выполняется только при прямом запуске файла.
if __name__ == "__main__":
    raise SystemExit(main())
