# pylint: disable = C0116, C0115, C0114, C0411

from __future__ import annotations

import os
import sys
import webbrowser
from functools import lru_cache
from pathlib import Path
from typing import Literal

import mdv
import pydantic_core
import toml
import tomllib
from dotenv import load_dotenv
from openai import OpenAI
from prompt_toolkit import Application, PromptSession
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.shortcuts import clear
from pydantic import BaseModel, ConfigDict

STARTUP_MESSAGE = (
    'INFO: Press "CTRL" + "D" to submit prompt '
    "or to pass through this info message.\n"
    'Press "CTRL" + "Z" during the AI\'s response '
    "to undo the message of the conversation.\n"
    'Press "CTRL" + "C" during input selection to exit.'
)
WAITING_MESSAGE = "Processing..."
CONFIG_FILE = "config.toml"
LOG_NAME = "conversation_log.md"

HOME = Path(__file__).resolve().parent
# issues:
# 1: make it so you enter the cli you only handle config after alternate buffer but before the info message
# 2: make the api key get actually saved into env


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
    environ_key: str = "API_KEY"
    endpoint: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    model_config = ConfigDict(str_min_length=2, frozen=True)


def config_wiz(data: dict) -> Config:
    while True:
        try:
            config_data = Config(**data)
        except pydantic_core.ValidationError as err_array:
            print(f"Configuration error from {CONFIG_FILE}:\n")
            for err in err_array.errors():
                print(
                    f"Invalid field: {err['loc'][0]}"
                )  # there should not be nesting in a TOML so index[0] is fine
                print(f"Error type: {err['msg']}")
                new_value = input("Enter new value: ")
                data[err["loc"][0]] = new_value
        else:
            break
    write_config({"main": config_data.model_dump()})
    return config_data


def get_api_key() -> str:
    env_key = get_config().environ_key
    denv = HOME / ".env"
    load_dotenv(dotenv_path=denv)
    try:
        return os.environ[env_key]
    except KeyError:
        api_key = input(
            f"Enter your the API key used for the {get_config().model} model here:\n>"
        )
        denv.write_text(f"{env_key}={api_key}\n")
        os.environ[env_key] = api_key  # not really necessary
        return api_key


def get_api() -> OpenAI:
    client = OpenAI(
        base_url=get_config().endpoint,
        api_key=get_api_key(),
    )
    return client


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
    formatted_contents = format_msgs(contents)

    with file.open(mode="w", encoding="utf-8") as writey:
        writey.write(formatted_contents)


def keypress_to_exit(*comboes: str, messages: MessagesArray | None = None) -> None:
    """exits when user inputs the specified combo"""
    kb = KeyBindings()
    deleted: list[Message] = []

    if messages:

        @kb.add("c-z")
        def _(_):
            if len(messages) > 0 and messages[-1].role != "developer":
                m = messages.pop(-1)
                deleted.append(m)
                print(
                    f'Deleted last message, by {m.role} with {len(m.content)} characters. Press "CONTROL" + "Y" to undo'
                )

        @kb.add("c-y")
        def _(_):
            if len(deleted) > 0:
                m = deleted.pop(-1)
                messages.append(m)
                print(
                    f"Undid last message deletion, was written by {m.role} and had {len(m.content)} characters"
                )

    @kb.add(*comboes)
    def exit_(event):
        event.app.exit()

    app = Application(key_bindings=kb, full_screen=False, layout=Layout(Window()))
    app.run()


def multiline_editor(initial: str = ""):
    kb = KeyBindings()

    @kb.add("enter")
    def _(event):
        event.current_buffer.insert_text("\n")

    @kb.add("c-d")
    def _(event):
        event.current_buffer.validate_and_handle()

    # buffer = Buffer(document=Document(initial))
    session = PromptSession(
        message=">> ",
        multiline=True,
        cursor=CursorShape.BLINKING_BEAM,
        key_bindings=kb,
        prompt_continuation=lambda width, line_number, is_soft_wrap: ">> ",
    )

    try:
        received_input = session.prompt(default=initial)
    except KeyboardInterrupt:
        return "", True

    return received_input, False


def make_query(client: OpenAI, messages: MessagesArray) -> str | None:
    response = client.chat.completions.create(
        model=get_config().model,
        messages=messages.to_list(),  # type: ignore
    )
    if response.choices:
        return response.choices[0].message.content
    print(f"\nD: an ERROR!!!: {response}")
    return None


def conversation_loop(messages: MessagesArray, api: OpenAI):
    while True:
        clear()
        print("Enter prompt:")
        query, is_exit = multiline_editor()
        if is_exit:
            break

        clear()
        print(WAITING_MESSAGE, end="", flush=True)
        messages.append(Message(role="user", content=query))
        response = make_query(api, messages)
        if not response:
            print("ERROR: did not recieve response from API. Exiting on input.")
            keypress_to_exit("enter", "escape", "c-d", "c-c")
            break

        print(f"\r{' ' * len(WAITING_MESSAGE)}\r", end="", flush=True)
        print(mdv.main(response))
        messages.append(Message(role="assistant", content=response))
        update_log(contents=messages)
        keypress_to_exit("c-d", messages=messages)
        conversation_loop(messages, api)


def orchestrate(api: OpenAI) -> None:
    messages = MessagesArray()
    conversation_loop(messages, api)


def startup() -> None:
    delete_log()
    with AlternateBuffer():
        clear()
        get_config()
        clear()
        api = get_api()
        clear()
        print(STARTUP_MESSAGE)
        keypress_to_exit("c-d")
        clear()
        orchestrate(api)
        clear()


if __name__ == "__main__":
    startup()
else:
    webbrowser.open("https://youtu.be/dQw4w9WgXcQ")
