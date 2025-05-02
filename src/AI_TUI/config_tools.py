# pylint: disable = C0116, C0115, C0114, C0411

from __future__ import annotations

from pathlib import Path

import mdv
import questionary
import tomllib

from AI_TUI import main

EDITOR_MESSAGE = (
    'INFO: Press "CTRL" + "D" to save.\n'
    'INFO: Press "CTRL" + "C" to cancel.\n'
    "WARN: api_endpoint setting is not used if your model type is gemini."
)


def text_edit(initial: str = "", msg: str | None = None) -> tuple[str, bool]:
    """returns str, has_exited"""
    print(msg) if msg else None  # pylint: disable = W0106
    return main.multiline_editor(initial)


def edit_toml() -> None:
    file = Path(main.HOME) / main.CONFIG_FILE
    contents = file.read_text(encoding="utf-8")
    edited = text_edit(
        contents,
    )[0]
    main.clear()
    if edited:
        try:
            tomllib.loads(edited)
        except tomllib.TOMLDecodeError:
            print("Invalid TOML formatting.")
            return
        file.write_text(edited, encoding="utf-8")


def find_logs() -> None:
    folder = (Path(main.HOME) / main.LOG_NAME).parent
    log_name = Path(main.LOG_NAME)
    logs = {f.name: f for f in folder.glob(f"{log_name.stem}*") if not f.is_dir()}

    if len(logs) == 0:
        print("Log not found.")
        return None
    if len(logs) == 1:
        return read_log(next(iter(logs.values())))

    selected: str = questionary.select(
        message="Select log to view:", choices=list(logs.keys())
    ).ask()
    if selected in logs:
        return read_log(logs[selected])


def read_log(log: Path) -> None:
    contents = log.read_text(encoding="utf-8")
    print(mdv.main(contents))
    main.keypress_to_exit("c-d", "c-c", "enter", "escape")
    main.clear()


def startup() -> None | type[Exception]:
    main.clear()
    choices = {
        "Edit config.toml": edit_toml,
        "See conversation log": find_logs,
        "Go back to main program": None,
        "Exit program": Exception,
    }

    while True:
        answer = questionary.select(
            message="Select Procedure:", choices=list(choices.keys())
        ).ask(kbi_msg="")
        main.clear()
        if not answer:  # for kbi
            return None
        result = choices[answer]
        if result is None or result is Exception:
            return result  # type: ignore why does pylance think this could be a callable

        if callable(result):
            result()


if __name__ == "__main__":
    with main.AlternateBuffer():
        startup()
