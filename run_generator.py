from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path.home() / "Desktop" / "Результаты генератора 2"
DEFAULT_BRAND = "Генератор 2"
DEFAULT_BRAND_NOTE = "Только для личного использования"


def build_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple Windows wrapper for the new embroidery generator")
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument("--output-name", default="", help="Base name for output files")
    parser.add_argument("--output-dir", default="", help="Output directory")
    parser.add_argument("--width", type=int, default=180, help="Pattern width in stitches")
    parser.add_argument("--colors", type=int, default=30, help="Maximum number of colors")
    parser.add_argument("--aida", type=int, default=14, help="Aida count")
    parser.add_argument("--title", default="", help="PDF title")
    parser.add_argument("--no-blends", action="store_true", help="Disable blend detection")
    parser.add_argument("--no-oxs", action="store_true", help="Disable OXS export")
    return parser


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
    image_path = Path(image).expanduser().resolve()
    if not image_path.exists():
        raise SystemExit(f"Image not found: {image_path}")

    base_dir = Path(__file__).resolve().parent
    script_path = base_dir / "scripts" / "generate_pattern.py"
    if not script_path.exists():
        raise SystemExit(f"Generator script not found: {script_path}")

    resolved_output_dir = Path(output_dir).expanduser().resolve() if output_dir else DEFAULT_OUTPUT_DIR
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    resolved_output_name = output_name.strip() or image_path.stem
    resolved_title = title.strip() or image_path.stem
    output_pdf = resolved_output_dir / f"{resolved_output_name}.pdf"

    command = [
        sys.executable,
        str(script_path),
        "--image",
        str(image_path),
        "--output",
        str(output_pdf),
        "--width",
        str(width),
        "--max-colors",
        str(colors),
        "--aida",
        str(aida),
        "--title",
        resolved_title,
        "--brand",
        DEFAULT_BRAND,
        "--brand-note",
        DEFAULT_BRAND_NOTE,
    ]
    if not use_blends:
        command.append("--no-blends")
    if no_oxs:
        command.append("--no-oxs")
    return command, output_pdf


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
    subprocess.run(
        command,
        check=True,
        cwd=Path(__file__).resolve().parent,
        env=build_subprocess_env(),
    )
    return output_pdf


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
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

    print("Running:")
    print(" ".join(f'"{part}"' if " " in part else part for part in command))
    print()
    subprocess.run(
        command,
        check=True,
        cwd=Path(__file__).resolve().parent,
        env=build_subprocess_env(),
    )
    print()
    print(f"Done: {output_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
