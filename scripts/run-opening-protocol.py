#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_SCRIPT = ROOT / "scripts" / "opening-dashboard.py"


def normalize_python_path(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if len(value) > 3 and value[0] == "/" and value[2] == "/" and value[1].isalpha():
        return f"{value[1].upper()}:{value[2:]}".replace("/", "\\")
    return value


def probe_python(candidate: str | Path | None) -> str | None:
    if not candidate:
        return None
    try:
        result = subprocess.run(
            [str(candidate), "-c", "import sys; print(sys.executable)"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            capture_output=True,
        )
    except (OSError, ValueError):
        return None

    if result.returncode != 0:
        return None

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if lines:
        actual = normalize_python_path(lines[-1])
        if actual:
            return actual
    return str(candidate)


def iter_python_candidates():
    candidates = [
        os.environ.get("OPENING_PROTOCOL_PYTHON"),
        os.environ.get("PYTHON"),
        sys.executable,
        shutil.which("python"),
        shutil.which("python.exe"),
        shutil.which("python3"),
        shutil.which("python3.exe"),
        shutil.which("py"),
        shutil.which("py.exe"),
    ]

    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        base = Path(userprofile) / "AppData" / "Local" / "Programs" / "Python"
        if base.exists():
            candidates.extend(sorted(base.glob("Python*/python.exe"), reverse=True))
        pythoncore_base = Path(userprofile) / "AppData" / "Local" / "Python"
        if pythoncore_base.exists():
            candidates.extend(sorted(pythoncore_base.glob("pythoncore-*/python.exe"), reverse=True))

    for base in (Path("C:/"), Path("C:/Program Files"), Path("C:/Program Files (x86)")):
        if base.exists():
            candidates.extend(sorted(base.glob("Python*/python.exe"), reverse=True))

    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        value = str(candidate)
        if value in seen:
            continue
        seen.add(value)
        yield value


def resolve_python() -> str | None:
    for candidate in iter_python_candidates():
        resolved = probe_python(candidate)
        if resolved:
            return resolved
    return None


def run_dashboard() -> str:
    python_path = resolve_python()
    if not python_path:
        return (
            "仪表盘输出失败：未找到可用的 Python 解释器。"
            "请先安装真实 Python，再运行 `python scripts/opening-dashboard.py`。"
        )

    result = subprocess.run(
        [python_path, str(DASHBOARD_SCRIPT)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="ignore",
        capture_output=True,
        env={**os.environ, "OPENING_PROTOCOL_PYTHON": python_path},
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "未知错误"
        return f"仪表盘输出失败：{detail}"
    return result.stdout.strip()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    print(run_dashboard())


if __name__ == "__main__":
    main()
