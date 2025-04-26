# pylint: disable = C0116, C0115, C0114, C0411

from __future__ import annotations

from pathlib import Path

import mdv
import questionary
import tomllib

import main


def text_edit(initial: str = "") -> tuple[str, bool]:
    """returns str, has_exited"""
    return main.multiline_editor(initial)


def edit_toml():
    file = Path(main.HOME) / main.CONFIG_FILE
    contents = file.read_text(encoding="utf-8")
    edited = text_edit(contents)[0]
    main.clear()
    if edited:
        try:
            tomllib.loads(edited)
        except tomllib.TOMLDecodeError:
            print("Invalid TOML formatting.")
            return
        file.write_text(edited, encoding="utf-8")


def conv_log():
    file = Path(main.HOME) / main.LOG_NAME
    if file.exists():
        contents = file.read_text(encoding="utf-8")
        print(mdv.main(contents))
        main.keypress_to_exit("c-d", "c-c", "enter", "escape")
        main.clear()
    else:
        print("Log not found.")


def startup():
    main.clear()
    choices = {
        "Edit config.toml": edit_toml,
        "See conversation log": conv_log,
        "Exit program": None,
    }

    while True:
        answer = questionary.select(
            message="Select Procedure:", choices=list(choices.keys())
        ).ask()
        if not answer:
            return
        main.clear()
        result = choices[answer]
        if result is None:
            return
        if callable(result):
            result()


if __name__ == "__main__":
    startup()
