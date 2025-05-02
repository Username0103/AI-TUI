# pylint: disable = C0116, C0115, C0114, C0411

from __future__ import annotations

from pathlib import Path
import json
from typing import TYPE_CHECKING

import openai
from openai import OpenAI
from google import genai
from google.genai import types
import google.genai.errors as g_error

from AI_TUI.tools import tools as tool_callables

if TYPE_CHECKING:
    from AI_TUI.main import MessagesArray, Config

ERROR_MESSAGE = "ERROR. press enter to continue"


def get_tools(home: Path) -> list[dict[str, str | dict]]:
    if (home / "src").exists():
        home = home / "src"

    tool_data = home / "tools" / "tools.json"

    if not tool_data.exists():
        raise FileNotFoundError(f"json tool data not found in {tool_data}")

    return json.loads(tool_data.read_text(encoding="utf-8"))["functions"]


def make_query_openai(
    client: OpenAI, messages: MessagesArray | list, config: Config, home: Path
) -> str | None:
    try:
        response = client.responses.create(
            model=config.model,
            input=messages.to_list(),  # type: ignore
            tools=get_tools(home),  # type: ignore
        )
        has_called_tools = False

        for call in response.output:
            if call.type == "function_call":
                has_called_tools = True
                result = tool_callables.functions[call.name](**call.arguments)  # type: ignore
                _messages: list = messages.copy()
                _messages.append(call)
                _messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": str(result),
                    }
                )
                return make_query_openai(client, _messages, config, home)

        if not has_called_tools:
            return response.output_text

    except openai.RateLimitError:
        print("Too many requests. Try again later.")
        return None

    except openai.OpenAIError as err:
        print(err or "")
        print(f"ERROR MSG: {getattr(err, 'message', 'None avaliable')}")
        input(ERROR_MESSAGE)
        return None


def get_gemini_tools(home: Path) -> types.Tool:
    return types.Tool(function_declarations=[*get_tools(home)])  # type: ignore


def make_query_gemini(
    client: genai.Client,
    messages: list[types.Content],
    config: Config,
    model_config: types.GenerateContentConfig,
) -> str | None:
    try:
        response = client.models.generate_content(
            model=config.model, contents=messages, config=model_config
        )
    except g_error.APIError as e:
        print(e)
        input(ERROR_MESSAGE)
        return None

    if response.function_calls:
        return handle_gemini_tools(response, client, messages, config, model_config)

    elif response.text:
        return response.text

    print(f"ERROR: {response}")
    input(ERROR_MESSAGE)
    return None


def handle_gemini_tools(
    response,
    client: genai.Client,
    messages: list[types.Content],
    config: Config,
    model_config: types.GenerateContentConfig,
) -> str | None:
    for call in response.function_calls:
        if not call.name:
            raise ValueError(
                f"invalid function call in {make_query_gemini.__name__}: {call}"
            )

        result = tool_callables.functions[call.name](**call.args)  # type: ignore
        function_response_part = types.Part.from_function_response(
            name=call.name,
            response={"result": result},
        )
        messages.extend(add_function_call_content(call, function_response_part))
        return make_query_gemini(client, messages, config, model_config)


def add_function_call_content(
    call: types.FunctionCall, response: types.Part
) -> list[types.Content]:
    return [
        types.Content(role="model", parts=[types.Part(function_call=call)]),
        types.Content(role="user", parts=[response]),
    ]


def google_messages_formatter(
    messages: MessagesArray, home: Path
) -> tuple[list[types.Content], types.GenerateContentConfig]:
    config = types.GenerateContentConfig(
        system_instruction=messages[0].content, tools=[get_gemini_tools(home)]
    )

    roles = ["model" if m.role == "assistant" else "user" for m in messages[1:]]
    return [
        types.Content(parts=[types.Part(text=m.content)], role=r)
        for m, r in zip(messages[1:], roles)
    ], config


def make_query(
    api_key: str, messages: MessagesArray, config: Config, home: Path
) -> str | None:
    if config.api_type == "google":
        api = genai.Client(api_key=api_key)
        msgs, model_config = google_messages_formatter(messages, home)
        return make_query_gemini(api, msgs, config, model_config)

    if config.api_type == "openai":
        api = OpenAI(
            base_url=config.endpoint,
            api_key=api_key,
        )
        return make_query_openai(api, messages, config, home)

    raise TypeError


if __name__ == "__main__":
    print("Do not run this module, run main.py instead.")
