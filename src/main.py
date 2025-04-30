# pylint: disable = C0116, C0115, C0114, C0411

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal, NoReturn

import mdv
import pydantic_core
import requests
import toml
import tomllib
from dotenv import load_dotenv
from prompt_toolkit import Application, PromptSession
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.shortcuts import clear, confirm
from pydantic import BaseModel, ConfigDict

import config_tools
from backend import make_query

STARTUP_MESSAGE = (
    'INFO: Press "CTRL" + "D" to submit prompt '
    "or to pass through this info message.\n"
    'Press "CTRL" + "Z" to undo the '
    "last message of the conversation.\n"
    'Press "CTRL" + "C" to exit.'
)
WAITING_MESSAGE = "Processing..."
CONFIG_FILE = "config.toml"
LOG_NAME = "conversation_log.md"
ENV_KEY = "API_KEY"
CONTINUE_KEYS = ("c-d", "enter", "escape", "q", "c-q")
GLOBAL_KEYS = KeyBindings()
deleted: list[Message] = []


def get_home() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


HOME = get_home()


@lru_cache
def get_config() -> Config:
    file = HOME / CONFIG_FILE
    if not file.exists():
        file.touch()
    with file.open("rb") as f:
        data = tomllib.load(f)
    if "main" not in data:
        data["main"] = {}
    return config_wiz(data["main"])


def write_config(data: dict):
    file = HOME / CONFIG_FILE
    with file.open("w") as f:
        toml.dump(data, f)


class Config(BaseModel):
    # the defaults can change via the TOML config
    prompt: str = "You are a helpful assistant."
    model: str = "gemini-2.5-flash-preview-04-17"
    model_type: Literal["google", "openai"] = "google"
    endpoint: str = "https://generativelanguage.googleapis.com/v1beta/"
    model_config = ConfigDict(str_min_length=2, frozen=True)


def config_wiz(data: dict) -> Config:
    while True:
        try:
            config_data = Config(**data)
        except pydantic_core.ValidationError as err_list:
            print(f"Configuration error from {CONFIG_FILE}:\n")
            for err in err_list.errors():
                # there should not be nesting in a TOML so index[0] is fine ->
                field = err["loc"][0]
                print(f"Invalid field: {field}")
                print(f"Value was: {data[field]}")
                print(f"Error type: {err['msg']}")
                new_value = input("Enter new value: ")
                data[err["loc"][0]] = new_value
        else:
            break
    write_config({"main": config_data.model_dump()})
    return config_data


def check_connection(timeout=5):
    url = get_config().endpoint
    try:
        _ = requests.head(url=url, timeout=timeout, allow_redirects=True)
        return True
    except requests.ConnectionError:
        return False


def get_api_key() -> str:
    denv = HOME / ".env"
    load_dotenv(dotenv_path=denv)
    try:
        return os.environ[ENV_KEY]
    except KeyError:
        api_key = input(
            f"Enter the API key used for the {get_config().model} model here:\n>"
        )
        denv.write_text(f"{ENV_KEY}={api_key}\n")
        os.environ[ENV_KEY] = api_key  # not really necessary
        return api_key


def add_global_bindings(messages: MessagesArray):
    kb = GLOBAL_KEYS

    @kb.add("c-z")
    def _undo(_):
        if len(messages) > 0 and messages[-1].role != "developer":
            m = messages.pop(-1)
            deleted.append(m)
            run_in_terminal(
                lambda: print(
                    f"Deleted last message, by {m.role} with {len(m.content)} "
                    'characters. Press "CONTROL" + "Y" to undo'
                )
            )

    @kb.add("c-y")
    def _redo(_):
        if len(deleted) > 0:
            m = deleted.pop(-1)
            messages.append(m)
            run_in_terminal(
                lambda: print(
                    "Undid last message deletion, was written by "
                    f"{m.role} and had {len(m.content)} characters"
                )
            )


def delete_log():
    log = HOME / LOG_NAME
    log.unlink(missing_ok=True)


class AlternateBuffer:
    def __enter__(self):
        # ANSI sequence to enter the buffer
        sys.stdout.write("\x1b[?1049h")
        sys.stdout.flush()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # ANSI sequence to exit the buffer
        sys.stdout.write("\x1b[?1049l")
        sys.stdout.flush()


class Message:
    def __init__(
        self,
        role: Literal["user", "developer", "assistant"],
        content: str,
    ):
        self.role = role
        self.content = content

    def to_dict(self):
        return {"role": self.role, "content": self.content}


class MessagesArray(list[Message]):
    def __init__(self, initial=None) -> None:
        super().__init__(initial or [])
        self.insert(0, Message(role="developer", content=get_config().prompt))

    def to_list(self) -> list[dict[str, str]]:
        return [m.to_dict() for m in self]


def format_msgs(m_array: MessagesArray | tuple[Message, ...]) -> str:
    return "".join(f"### {m.role.capitalize()}:\n{m.content}\n\n" for m in m_array)


def update_log(contents: MessagesArray) -> None:
    file = HOME / LOG_NAME
    file.write_text(format_msgs(contents), encoding="utf-8")


def keypress_to_exit(*combos: str) -> None:
    """exits when user inputs the specified combo"""
    kb = KeyBindings()

    def _exit(event):
        event.app.exit()

    for combo in combos:
        kb.add(combo)(_exit)

    app = Application(key_bindings=kb, full_screen=False, layout=Layout(Window()))
    app.run()


def multiline_editor(initial: str = "") -> tuple[str, bool]:
    kb = KeyBindings()

    @kb.add("enter")
    def _(event):
        event.current_buffer.insert_text("\n")

    @kb.add("c-d")
    def _(event):
        event.current_buffer.validate_and_handle()

    merged = merge_key_bindings([kb, GLOBAL_KEYS])

    session = PromptSession(
        message=">> ",
        multiline=True,
        key_bindings=merged,
        cursor=CursorShape.BLINKING_BEAM,
        prompt_continuation=lambda width, line_number, is_soft_wrap: ">> ",
    )

    try:
        received_input = session.prompt(default=initial)
    except KeyboardInterrupt:
        return "", True

    return received_input, False


def conversation_loop(messages: MessagesArray, api_key: str):
    while True:
        clear()
        print("Enter prompt:")
        query, is_exit = multiline_editor()
        if is_exit:
            break

        clear()
        print(WAITING_MESSAGE, end="", flush=True)
        messages.append(Message(role="user", content=query))
        response = make_query(api_key, messages, get_config())
        if not response:
            print("ERROR: did not receive response from API. Exiting on input.")
            keypress_to_exit(*CONTINUE_KEYS)
            break

        print(f"\r{' ' * len(WAITING_MESSAGE)}\r", end="", flush=True)
        print(mdv.main(response))
        messages.append(Message(role="assistant", content=response))
        update_log(contents=messages)
        keypress_to_exit("c-d")


def orchestrate() -> None:
    clear()
    messages = MessagesArray()
    add_global_bindings(messages)
    delete_log()
    api_key = get_api_key()
    conversation_loop(messages, api_key)


def see_if_options() -> None | NoReturn:
    try:
        answer = confirm("Enter options/log menu? You will be able to return.")
    except KeyboardInterrupt:
        sys.exit()
    if answer:
        if config_tools.startup() is Exception:
            sys.exit()


def startup() -> None:
    with AlternateBuffer():
        clear()
        get_config()
        clear()
        see_if_options()
        clear()
        if check_connection():
            print(STARTUP_MESSAGE)
            keypress_to_exit(*CONTINUE_KEYS)
            orchestrate()
        else:
            print("Connection error. Check if your internet and the API are online.")
            keypress_to_exit(*CONTINUE_KEYS)


if __name__ == "__main__":
    startup()
