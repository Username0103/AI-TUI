# pylint: disable = C0116, C0115, C0114

import sys
from pathlib import Path

import mdv
from openai import OpenAI
from prompt_toolkit import Application, PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.shortcuts import clear

STARTUP_MESSAGE = (
    'INFO: Press "CTRL" + "D" to submit prompt'
    ' or to pass through this info message.\n'
    'Press "CTRL" + "C" during input to exit.'
)
WAITING_MESSAGE = "Processing..."
API_URL = 'https://generativelanguage.googleapis.com/v1beta/' #
# API_URL = "https://openrouter.ai/api/v1"
CURRENT_MODEL = 'gemini-2.0-flash'
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


def keypress_to_exit(combo) -> None:
    """exits when user inputs the specified combo"""
    kb = KeyBindings()

    @kb.add(combo)
    def exit_(event):
        event.app.exit()

    app = Application(key_bindings=kb, full_screen=False, layout=Layout(Window()))
    app.run()


def get_input():
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

    return received_input


def make_query(client: OpenAI, messages) -> str | None:
    response = client.chat.completions.create(model=CURRENT_MODEL, messages=messages)
    if response.choices:
        return response.choices[0].message.content
    print(f"\nD: an ERROR!!!: {response}")
    return None


def update_log(*args: dict) -> None:
    file = home / LOG_NAME
    with file.open(mode='a', encoding="utf-8") as appendable:
        for message_dict in args:
            role = str(message_dict.get('role'))
            content = str(message_dict.get('content'))
            appendable.write(f'### {role.capitalize()}:\n{content}\n\n')

def delete_log():
    log = home / LOG_NAME
    log.unlink(missing_ok=True)

def conversate(messages: list, api: OpenAI):
    '''I don't mind a good RecursionError'''
    clear()
    print("Enter prompt:")
    query = get_input()
    clear()
    print(WAITING_MESSAGE, end="", flush=True)
    messages.append({"role": "user", "content": query})
    response = make_query(api, messages)
    if not response:
        print("ERROR: did not recieve response from API. Exiting...")
        return None
    print(f"\r{' ' * len(WAITING_MESSAGE)}\r", end="", flush=True)
    print(mdv.main(response))
    messages.append({"role": "assistant", "content": response})
    update_log(messages[-2], messages[-1])
    keypress_to_exit('c-d')
    conversate(messages, api)


def orchestrate() -> None:
    key = get_key()
    api = get_api(key)
    conversate([], api)


def startup():
    delete_log()
    with AlternateBuffer():
        print(STARTUP_MESSAGE)
        keypress_to_exit('c-d')
        clear()
        orchestrate()
        clear()

if __name__ == "__main__":
    startup()
