# pylint: disable = C0116, C0115, C0114, C0411

from __future__ import annotations

from typing import TYPE_CHECKING

import openai
from openai import OpenAI
from google import genai
from google.genai import types
import google.genai.errors as g_error

if TYPE_CHECKING:
    from main import MessagesArray, Config

ERROR_MESSAGE = "ERROR. press enter to continue\n"


def make_query_openai(
    client: OpenAI, messages: MessagesArray, config: Config
) -> str | None:
    try:
        response = client.responses.create(
            model=config.model,
            input=messages.to_list(),  # type: ignore
        )

        return response.output_text

    except openai.RateLimitError:
        print("Too many requests. Try again later.")
        return None

    except openai.OpenAIError as err:
        print(err or "")
        print(f"ERROR MSG: {getattr(err, 'message', '')}")
        input(ERROR_MESSAGE)
        return None


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

    if response.text:
        return response.text

    input(ERROR_MESSAGE)
    return None


def google_messages_formatter(
    messages: MessagesArray,
) -> tuple[list[types.Content], types.GenerateContentConfig]:
    dev_msg = messages.copy().pop(0)
    config = types.GenerateContentConfig(system_instruction=dev_msg.content)

    roles = ["model" if m.role == "assistant" else "user" for m in messages]
    return [
        types.Content(parts=[types.Part(text=m.content)], role=r)
        for m, r in zip(messages, roles)
    ], config


def make_query(api_key: str, messages: MessagesArray, config: Config) -> str | None:
    if config.model_type == "google":
        api = genai.Client(api_key=api_key)
        msgs, model_config = google_messages_formatter(messages)
        return make_query_gemini(api, msgs, config, model_config)

    if config.model_type == "openai":
        api = OpenAI(
            base_url=config.endpoint,
            api_key=api_key,
        )
        return make_query_openai(api, messages, config)

    raise TypeError
