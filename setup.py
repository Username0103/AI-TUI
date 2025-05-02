# pylint: disable = C0116, C0115, C0114, C0411

from setuptools import setup, find_packages
from subprocess import check_output as out
from subprocess import SubprocessError


def get_version() -> str:
    try:
        return out(
            ["git", "describe", "--tags", "--abbrev=0"], universal_newlines=True
        ).strip().rsplit("v", maxsplit=1)[-1]
    except SubprocessError:
        return "1.0.0"

setup(
    name="AI-TUI",
    version=get_version(),
    package_dir={"": "src"},
    packages=find_packages(where='src'),
    entry_points={
        "console_scripts": [
            "ai-tui=AI_TUI.entry:main",
        ],
    },
)
