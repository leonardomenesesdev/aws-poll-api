"""Gera o lambda.zip para deploy na AWS.

Dois cuidados que este script resolve e que quebram o deploy silenciosamente:

1. O Compress-Archive do Windows PowerShell 5.1 grava as entradas do zip com '\'
   como separador, mas o formato ZIP exige '/'. O Lambda (Linux) passa a ver
   'app\\main.py' como nome literal de arquivo em vez da pasta 'app/'.
   Aqui usamos o modulo zipfile, que sempre grava '/'.

2. pydantic-core traz uma extensao compilada. Instalado no Windows, o pip baixa
   um .pyd win_amd64 que nao carrega no Lambda. Por isso forcamos o download das
   wheels manylinux (Linux x86_64), independente de onde o script roda.

Uso (a partir da raiz do projeto, com o venv ativo):
    python scripts/build_lambda_package.py
"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build" / "lambda"
ZIP_PATH = ROOT / "lambda.zip"

# boto3/botocore ja vem no runtime da Lambda, entao ficam de fora do pacote.
DEPENDENCIES = [
    "fastapi==0.115.0",
    "mangum==0.19.0",
    "pydantic==2.9.2",
    "python-dotenv==1.0.1",
]

EXCLUDED_DIRS = {"__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}

# Runtime da Lambda: Python 3.12 em Linux x86_64.
LAMBDA_PLATFORM = "manylinux2014_x86_64"
LAMBDA_PYTHON_VERSION = "3.12"


def install_dependencies() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    subprocess.run(
        [
            sys.executable, "-m", "pip", "install", "--quiet",
            "--target", str(BUILD_DIR),
            "--platform", LAMBDA_PLATFORM,
            "--python-version", LAMBDA_PYTHON_VERSION,
            "--implementation", "cp",
            # --platform exige que nada seja compilado localmente.
            "--only-binary=:all:",
            *DEPENDENCIES,
        ],
        check=True,
    )


def should_include(path: Path) -> bool:
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return not EXCLUDED_DIRS.intersection(path.parts)


def add_tree(zf: zipfile.ZipFile, source_dir: Path, base_dir: Path) -> int:
    count = 0
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or not should_include(path):
            continue
        # as_posix() garante '/' como separador, exigido pelo formato ZIP.
        zf.write(path, path.relative_to(base_dir).as_posix())
        count += 1
    return count


def verify_zip() -> None:
    """Falha alto em vez de gerar um pacote que so quebra depois do deploy."""
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zf.namelist()

    problems = []

    backslash = [n for n in names if "\\" in n]
    if backslash:
        problems.append(f"{len(backslash)} entradas com '\\' no lugar de '/' (ex: {backslash[0]})")

    windows_bins = [n for n in names if n.endswith((".pyd", ".dll"))]
    if windows_bins:
        problems.append(f"binarios Windows no pacote (ex: {windows_bins[0]})")

    if "app/lambda_handler.py" not in names:
        problems.append("app/lambda_handler.py ausente -- o Handler nao seria encontrado")

    if problems:
        for problem in problems:
            print(f"  ERRO: {problem}", file=sys.stderr)
        sys.exit(1)


def build_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        deps = add_tree(zf, BUILD_DIR, BUILD_DIR)
        app = add_tree(zf, ROOT / "app", ROOT)

    verify_zip()

    size_mb = ZIP_PATH.stat().st_size / 1024 / 1024
    print(f"{ZIP_PATH.name}: {deps} arquivos de dependencias + {app} do app ({size_mb:.1f} MB)")


if __name__ == "__main__":
    install_dependencies()
    build_zip()
