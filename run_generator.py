# =============================================================================
#  run_generator.py
# -----------------------------------------------------------------------------
#  Тонкая CLI-обёртка вокруг основного скрипта-генератора схем для вышивки
#  крестиком (scripts/generate_pattern.py).
#
#  Назначение модуля:
#    * собрать корректный набор аргументов командной строки для дочернего
#      процесса, учитывая пути, кодировки и значения по умолчанию;
#    * предоставить GUI-приложению (gui_app.py) функции build_command() и
#      build_subprocess_env(), чтобы оно могло запускать генератор в отдельном
#      потоке и читать его вывод построчно;
#    * дать возможность запуска этого же генератора напрямую из консоли
#      (python run_generator.py --image ...).
#
#  Структура файла:
#    1. Импорты и константы
#    2. Подготовка окружения подпроцесса
#    3. Разбор аргументов командной строки
#    4. Сборка команды запуска дочернего генератора
#    5. Высокоуровневая функция-запускатор (run_generator)
#    6. Точка входа при прямом запуске файла (main)
# =============================================================================

from __future__ import annotations  # отложенное вычисление аннотаций типов

# -----------------------------------------------------------------------------
# 1. ИМПОРТЫ И КОНСТАНТЫ
# -----------------------------------------------------------------------------
import argparse      # парсер аргументов командной строки
import os            # работа с переменными окружения операционной системы
import subprocess    # запуск дочерних процессов (сам генератор запускается так)
import sys           # sys.executable — путь к текущему интерпретатору Python
from pathlib import Path  # удобная кроссплатформенная работа с путями


# Папка, куда по умолчанию будут сохраняться готовые PDF-схемы и превью.
# Используется рабочий стол пользователя + русская подпапка "Результаты генератора 2".
DEFAULT_OUTPUT_DIR = Path.home() / "Desktop" / "Результаты генератора 2"

# Название бренда, которое печатается в подвале каждого листа PDF.
DEFAULT_BRAND = "Генератор 2"

# Краткая приписка к бренду (например, ограничение лицензии).
DEFAULT_BRAND_NOTE = "Только для личного использования"


# -----------------------------------------------------------------------------
# 2. ПОДГОТОВКА ОКРУЖЕНИЯ ПОДПРОЦЕССА
# -----------------------------------------------------------------------------
def build_subprocess_env() -> dict[str, str]:
    """Возвращает словарь переменных окружения для дочернего Python-процесса.

    На Windows стандартная кодировка консоли часто cp1251, из-за чего вывод
    с кириллицей превращается в "кракозябры". Мы принудительно включаем UTF-8
    через переменные PYTHONIOENCODING и PYTHONUTF8, чтобы print() в дочернем
    скрипте корректно писал русские сообщения в stdout.
    """
    # Копируем текущее окружение, чтобы не потерять PATH, TEMP и т.д.
    env = os.environ.copy()
    # Кодировка, в которой Python будет писать в stdout/stderr.
    env["PYTHONIOENCODING"] = "utf-8"
    # Включает UTF-8 Mode (PEP 540) — влияет на open(), sys.argv и т.п.
    env["PYTHONUTF8"] = "1"
    return env


# -----------------------------------------------------------------------------
# 3. РАЗБОР АРГУМЕНТОВ КОМАНДНОЙ СТРОКИ
# -----------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Создаёт и возвращает парсер аргументов CLI.

    Выделено в отдельную функцию, чтобы удобно было переиспользовать
    (например, в тестах или при автогенерации документации).
    """
    parser = argparse.ArgumentParser(
        description="Simple Windows wrapper for the new embroidery generator"
    )
    # --- Обязательный параметр: путь к исходному изображению ---
    parser.add_argument("--image", required=True, help="Path to input image")

    # --- Необязательные параметры с значениями по умолчанию ---
    # Базовое имя выходных файлов (без расширения). Пустая строка => возьмём stem изображения.
    parser.add_argument("--output-name", default="", help="Base name for output files")
    # Папка вывода. Пустая строка => DEFAULT_OUTPUT_DIR.
    parser.add_argument("--output-dir", default="", help="Output directory")
    # Ширина схемы в крестиках — влияет на детализацию.
    parser.add_argument("--width", type=int, default=180, help="Pattern width in stitches")
    # Максимальное количество цветов в итоговой палитре (к-means кластеризация).
    parser.add_argument("--colors", type=int, default=30, help="Maximum number of colors")
    # Каунт канвы Aida (11/14/16/18/20) — определяет физический размер вышивки.
    parser.add_argument("--aida", type=int, default=14, help="Aida count")
    # Заголовок, который будет напечатан на титульной странице PDF.
    parser.add_argument("--title", default="", help="PDF title")
    # Флаги-переключатели: по умолчанию False, включаются упоминанием в командной строке.
    parser.add_argument("--no-blends", action="store_true", help="Disable blend detection")
    parser.add_argument("--no-oxs", action="store_true", help="Disable OXS export")
    return parser


# -----------------------------------------------------------------------------
# 4. СБОРКА КОМАНДЫ ЗАПУСКА ДОЧЕРНЕГО ГЕНЕРАТОРА
# -----------------------------------------------------------------------------
def build_command(
    image: str,
    output_name: str = "",
    output_dir: str = "",
    width: int = 180,
    colors: int = 30,
    aida: int = 14,
    title: str = "",
    use_blends: bool = False,
    no_oxs: bool = False,
) -> tuple[list[str], Path]:
    """Формирует список аргументов для subprocess.Popen и путь к итоговому PDF.

    Возвращает кортеж (command, output_pdf):
        command    — список строк, готовый к передаче в subprocess.Popen/run;
        output_pdf — абсолютный путь к ожидаемому PDF-файлу после генерации.

    Функция:
      * проверяет наличие файла изображения и скрипта-генератора;
      * создаёт папку вывода (вместе с родительскими), если её нет;
      * подставляет осмысленные значения по умолчанию для имени и заголовка;
      * корректно преобразует булевы флаги в ключи командной строки.
    """
    # --- 4.1. Проверка и нормализация пути к изображению ---
    # expanduser() — раскрывает "~" в домашний каталог пользователя.
    # resolve()    — делает путь абсолютным и нормализует его (убирает "..", и т.д.).
    image_path = Path(image).expanduser().resolve()
    if not image_path.exists():
        # SystemExit позволяет единообразно обрабатывать ошибку в GUI (ловится как исключение).
        raise SystemExit(f"Image not found: {image_path}")

    # --- 4.2. Поиск скрипта-генератора рядом с этим файлом ---
    base_dir = Path(__file__).resolve().parent
    script_path = base_dir / "scripts" / "generate_pattern.py"
    if not script_path.exists():
        raise SystemExit(f"Generator script not found: {script_path}")

    # --- 4.3. Папка вывода: либо заданная пользователем, либо значение по умолчанию ---
    resolved_output_dir = (
        Path(output_dir).expanduser().resolve() if output_dir else DEFAULT_OUTPUT_DIR
    )
    # Создаём папку вывода, если её нет (parents=True — вместе с родительскими).
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    # --- 4.4. Умолчания для имени файла и заголовка ---
    # Если пользователь не задал имя — берём имя исходного изображения без расширения.
    resolved_output_name = output_name.strip() or image_path.stem
    resolved_title = title.strip() or image_path.stem
    # Полный путь к итоговому PDF.
    output_pdf = resolved_output_dir / f"{resolved_output_name}.pdf"

    # --- 4.5. Формирование списка аргументов дочернего процесса ---
    # Используем sys.executable, чтобы подпроцесс запускался тем же интерпретатором,
    # что и текущий — это важно для виртуальных окружений.
    command = [
        sys.executable,
        str(script_path),
        "--image", str(image_path),
        "--output", str(output_pdf),
        "--width", str(width),
        "--max-colors", str(colors),
        "--aida", str(aida),
        "--title", resolved_title,
        "--brand", DEFAULT_BRAND,
        "--brand-note", DEFAULT_BRAND_NOTE,
    ]

    # --- 4.6. Условные флаги ---
    # В GUI флаг называется use_blends (положительный), а в CLI — --no-blends (отрицательный),
    # поэтому инвертируем: если бленды НЕ используются, добавляем --no-blends.
    if not use_blends:
        command.append("--no-blends")
    # Отключение экспорта в OXS (формат Open Cross Stitch) — по желанию пользователя.
    if no_oxs:
        command.append("--no-oxs")

    return command, output_pdf


# -----------------------------------------------------------------------------
# 5. ВЫСОКОУРОВНЕВАЯ ФУНКЦИЯ-ЗАПУСКАТОР
# -----------------------------------------------------------------------------
def run_generator(
    image: str,
    output_name: str = "",
    output_dir: str = "",
    width: int = 180,
    colors: int = 30,
    aida: int = 14,
    title: str = "",
    use_blends: bool = False,
    no_oxs: bool = False,
) -> Path:
    """Синхронно запускает генератор и возвращает путь к созданному PDF.

    В отличие от build_command() эта функция сама выполняет subprocess.run
    и блокирует выполнение до завершения дочернего процесса. Подходит для
    случаев, когда нужен простой "скриптовый" запуск без GUI.
    """
    # Собираем команду и путь к итоговому файлу.
    command, output_pdf = build_command(
        image=image,
        output_name=output_name,
        output_dir=output_dir,
        width=width,
        colors=colors,
        aida=aida,
        title=title,
        use_blends=use_blends,
        no_oxs=no_oxs,
    )
    # check=True — если генератор вернёт ненулевой код, будет поднято CalledProcessError.
    # cwd — рабочая директория дочернего процесса (корень проекта).
    subprocess.run(
        command,
        check=True,
        cwd=Path(__file__).resolve().parent,
        env=build_subprocess_env(),
    )
    return output_pdf


# -----------------------------------------------------------------------------
# 6. ТОЧКА ВХОДА ПРИ ПРЯМОМ ЗАПУСКЕ ФАЙЛА
# -----------------------------------------------------------------------------
def main() -> int:
    """Вход при запуске `python run_generator.py ...` из командной строки."""
    # Разбираем аргументы командной строки.
    parser = build_parser()
    args = parser.parse_args()

    # Преобразуем разобранные аргументы в команду запуска генератора.
    # Обратите внимание: в CLI флаг называется --no-blends, поэтому use_blends = not args.no_blends.
    command, output_pdf = build_command(
        image=args.image,
        output_name=args.output_name,
        output_dir=args.output_dir,
        width=args.width,
        colors=args.colors,
        aida=args.aida,
        title=args.title,
        use_blends=not args.no_blends,
        no_oxs=args.no_oxs,
    )

    # Печатаем команду перед запуском — удобно для отладки и воспроизведения.
    print("Running:")
    print(" ".join(f'"{part}"' if " " in part else part for part in command))
    print()

    # Синхронный запуск дочернего процесса.
    subprocess.run(
        command,
        check=True,
        cwd=Path(__file__).resolve().parent,
        env=build_subprocess_env(),
    )

    print()
    print(f"Done: {output_pdf}")
    return 0


# Стандартный защитный блок: код внутри выполняется только при прямом запуске,
# но не при импорте модуля (например, из gui_app.py).
if __name__ == "__main__":
    raise SystemExit(main())
