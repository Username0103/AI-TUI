# pylint: disable = C0116, C0115, C0114

from __future__ import annotations
import sys
from pathlib import Path
from typing import Literal
import tomllib


import mdv
from openai import OpenAI
from prompt_toolkit import Application, PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.shortcuts import clear

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

home = Path(__file__).resolve().parent


def get_config():
    file = home / CONFIG_FILE
    if not file.exists():
        raise FileNotFoundError(f"Must place {file} file in {home} directory.")
    with file.open("rb") as f:
        data = tomllib.load(f)
    verify_config(data)
    return data


def verify_config(data: dict):
    try:
        m = data["main"]
        _ = m["model"], m["api-key"], m["prompt"]
    except KeyError as e:
        print(
            f"You need to have the {e.args[0]} section or value in your {CONFIG_FILE} file."
        )
        sys.exit(1)


config = get_config()["main"]


def get_api(api_key: str) -> OpenAI:
    client = OpenAI(
        base_url=config["endpoint"],
        api_key=f"{api_key}",
    )
    return client


def delete_log():
    log = home / LOG_NAME
    log.unlink(missing_ok=True)


class AlternateBuffer:
    def __enter__(self):
        # enter alternate buffer
        sys.stdout.write("\x1b[?1049h")
        sys.stdout.flush()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # exit alternate buffer
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
        self.insert(0, Message(role="developer", content=config["prompt"]))

    def to_list(self) -> list[dict[str, str]]:
        return [m.to_dict() for m in self]


def format_msgs(m_array: MessagesArray | tuple[Message, ...]) -> str:
    return "".join(f"### {m.role.capitalize()}:\n{m.content}\n\n" for m in m_array)


def update_log(*args: Message, old_contents: MessagesArray) -> None:
    file = home / LOG_NAME
    to_write = format_msgs(args)
    formatted_contents = format_msgs(old_contents)

    with file.open(mode="w", encoding="utf-8") as writey:
        writey.write(formatted_contents + to_write)


def keypress_to_exit(
    combo: str, allow_z: bool = False, messages: MessagesArray | None = None
) -> None:
    """exits when user inputs the specified combo"""
    kb = KeyBindings()
    deleted: list[Message] = []

    if allow_z:
        if not messages:
            name = sys._getframe().f_code.co_name  # pylint: disable = W0212
            raise ValueError(
                f"Must have messages array in {name} call if allow_z is true"
            )

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

    @kb.add(combo)
    def exit_(event):
        event.app.exit()

    app = Application(key_bindings=kb, full_screen=False, layout=Layout(Window()))
    app.run()


def get_input(messages: MessagesArray):
    bindings = KeyBindings()

    @bindings.add("enter")
    def _(event):
        event.current_buffer.insert_text("\n")

    @bindings.add("c-d")
    def _(event):
        event.current_buffer.validate_and_handle()

    try:
        received_input = PromptSession(
            message=">> ",
            multiline=True,
            key_bindings=bindings,
            prompt_continuation=lambda width, line_number, is_soft_wrap: ">> ",
        ).prompt()
    except KeyboardInterrupt:
        return "", messages, True

    return received_input, messages, False


def make_query(client: OpenAI, messages: MessagesArray) -> str | None:
    response = client.chat.completions.create(
        model=config["model"],
        messages=messages.to_list(),  # type: ignore
    )
    if response.choices:
        return response.choices[0].message.content
    print(f"\nD: an ERROR!!!: {response}")
    return None


def conversate(messages: MessagesArray, api: OpenAI):
    """I don't mind a good RecursionError"""
    clear()
    print("Enter prompt:")
    query, messages, is_exit = get_input(messages)
    if is_exit:
        return

    clear()
    print(WAITING_MESSAGE, end="", flush=True)
    messages.append(Message(role="user", content=query))
    response = make_query(api, messages)
    if not response:
        print("ERROR: did not recieve response from API. Exiting...")
        keypress_to_exit("c-d")
        return

    print(f"\r{' ' * len(WAITING_MESSAGE)}\r", end="", flush=True)
    print(mdv.main(response))
    messages.append(Message(role="assistant", content=response))
    update_log(messages[-2], messages[-1], old_contents=messages)
    keypress_to_exit("c-d", True, messages)
    conversate(messages, api)


def orchestrate() -> None:
    messages = MessagesArray()
    key = config["api-key"]
    api = get_api(key)
    conversate(messages, api)


def startup() -> None:
    delete_log()
    with AlternateBuffer():
        print(STARTUP_MESSAGE)
        keypress_to_exit("c-d")
        clear()
        orchestrate()
        clear()


if __name__ == "__main__":
    startup()
