from pathlib import Path
import subprocess
import sys
import runpy


PROJECT_ROOT = Path(__file__).resolve().parent
INNER_APP = PROJECT_ROOT / "UDAAN-main" / "app.py"
REQUIREMENTS_FILE = PROJECT_ROOT / "UDAAN-main" / "requirements.txt"


def ensure_dependencies() -> None:
    required_modules = ("flask", "flask_sqlalchemy", "flask_bcrypt", "pymysql")

    try:
        for module_name in required_modules:
            __import__(module_name)
    except ModuleNotFoundError as exc:
        if not REQUIREMENTS_FILE.exists():
            raise RuntimeError(
                f"Missing dependency '{exc.name}' and requirements file was not found at: {REQUIREMENTS_FILE}"
            ) from exc

        print(
            f"Installing missing dependency '{exc.name}' for interpreter: {sys.executable}",
            flush=True,
        )
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)])

if not INNER_APP.exists():
    raise FileNotFoundError(f"Could not find app entrypoint at: {INNER_APP}")

ensure_dependencies()
runpy.run_path(str(INNER_APP), run_name="__main__")
