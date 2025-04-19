# pylint: disable = C0116, C0115, C0114

from __future__ import annotations
import sys
from pathlib import Path
from typing import Literal


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
    "to undo the message of conversation\n"
    'Press "CTRL" + "C" during input to exit.'
)
WAITING_MESSAGE = "Processing..."
API_URL = "https://generativelanguage.googleapis.com/v1beta/"  #
# API_URL = "https://openrouter.ai/api/v1"
CURRENT_MODEL = "gemini-2.0-flash"
# CURRENT_MODEL = "google/gemini-2.5-pro-exp-03-25:free"
API_FILE_NAME = "api.txt"
PROMPT_FILE_NAME = "prompt.txt"
LOG_NAME = "conversation_log.md"

home = Path(__file__).resolve().parent


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
        self.insert(0, Message(role="developer", content=get_prompt()))

    def to_list(self) -> list[dict[str, str]]:
        return [m.to_dict() for m in self]


def check_txt_existence(folder: Path, file: str):
    if (folder / file).exists():
        return True
    raise FileNotFoundError(f"Must place {file} in {folder}")


def get_key() -> str:
    check_txt_existence(home, API_FILE_NAME)
    file = home / API_FILE_NAME
    with file.open(encoding="utf-8") as s:
        return s.read().strip()


def get_api(api_key: str) -> OpenAI:
    client = OpenAI(
        base_url=API_URL,
        api_key=f"{api_key}",
    )
    return client


def keypress_to_exit(
    combo: str, allow_z: bool = False, messages: MessagesArray | None = None
) -> None:
    """exits when user inputs the specified combo"""
    kb = KeyBindings()
    deleted: list[Message] = []

    if allow_z:
        if not messages:
            raise ValueError("Must have messages array in call if allow_z is true")

        @kb.add("c-z")
        def _(_):
            if len(messages) > 0 and messages[-1].role != "developer":
                deleted.append(messages.pop(-1))
                print('Deleted last Conversation round. Press "CONTROL" + "Y" to undo')

        @kb.add("c-y")
        def _(_):
            if len(deleted) > 0:
                messages.append(deleted.pop(-1))
                print("Undid last message deletion")

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
        print("Exited program.")
        sys.exit()

    return received_input, messages


def make_query(client: OpenAI, messages: MessagesArray) -> str | None:
    response = client.chat.completions.create(
        model=CURRENT_MODEL,
        messages=messages.to_list(),  # type: ignore
    )
    if response.choices:
        return response.choices[0].message.content
    print(f"\nD: an ERROR!!!: {response}")
    return None


def format_msgs(m_array: MessagesArray | tuple[Message, ...]) -> str:
    return "".join(f"### {m.role.capitalize()}:\n{m.content}\n\n" for m in m_array)


def update_log(*args: Message, old_contents: MessagesArray) -> None:
    file = home / LOG_NAME
    to_write = format_msgs(args)
    formatted_contents = format_msgs(old_contents)

    with file.open(mode="w", encoding="utf-8") as writey:
        writey.write(formatted_contents + to_write)


def delete_log():
    log = home / LOG_NAME
    log.unlink(missing_ok=True)


def conversate(messages: MessagesArray, api: OpenAI):
    """I don't mind a good RecursionError"""
    clear()
    print("Enter prompt:")
    query, messages = get_input(messages)
    clear()
    print(WAITING_MESSAGE, end="", flush=True)
    messages.append(Message(role="user", content=query))
    response = make_query(api, messages)
    if not response:
        print("ERROR: did not recieve response from API. Exiting...")
        return None
    print(f"\r{' ' * len(WAITING_MESSAGE)}\r", end="", flush=True)
    print(mdv.main(response))
    messages.append(Message(role="assistant", content=response))
    update_log(messages[-2], messages[-1], old_contents=messages)
    keypress_to_exit("c-d", True, messages)
    conversate(messages, api)


def orchestrate() -> None:
    messages = MessagesArray()
    key = get_key()
    api = get_api(key)
    conversate(messages, api)


def get_prompt() -> str:
    file = home / PROMPT_FILE_NAME
    if not file.exists():
        raise FileNotFoundError(f"Must place a {file} file in {home}")
    with file.open() as s:
        contents = s.read()
    return contents


def startup():
    delete_log()
    with AlternateBuffer():
        print(STARTUP_MESSAGE)
        keypress_to_exit("c-d")
        clear()
        orchestrate()
        clear()


if __name__ == "__main__":
    startup()
