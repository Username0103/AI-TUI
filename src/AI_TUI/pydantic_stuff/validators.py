# pylint: disable = C0116, C0115, C0114, C0411
"""this is broken."""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import google.genai.errors as g_error
from google import genai
from openai import OpenAI
import openai
from pydantic import HttpUrl
from pydantic_core import PydanticCustomError
import requests

if TYPE_CHECKING:
    from .models import Config


def verify_endpoint(url: HttpUrl) -> HttpUrl:
    try:
        _ = requests.head(str(url), timeout=5)
        return url
    except requests.RequestException as err:
        raise PydanticCustomError(
            "Connection Error",
            "Unable to connect to the endpoint. {code} code.",
            {"code": err.response.status_code if err.response else "unknown"},
        ) from None

@lru_cache
def get_models_list(config: Config, key: str) -> list:
    if config.api_type == "google":
        client = genai.Client(api_key=key)
    else:
        client = OpenAI(api_key=key)

    models = list(client.models.list())  # polyglot coding

    return models


def verify_models_list(config: Config, key: str, selected_model: str) -> str:
    models = get_models_list(config, key)
    if selected_model not in models:
        raise PydanticCustomError(
            "Invalid model error",
            "Selected AI model not in the API's model list. Avaliable models: {models}",
            {"models": models},
        )
    return key


def verify_api_key(config: Config, key: str) -> str:
    if not key:
        raise PydanticCustomError(
            "Value error",
            "No API key provided",
        )
    try:
        get_models_list(config, key)
    except (g_error.APIError, openai.APIError):
        raise PydanticCustomError(
            "API error",
            "API key could not fetch models from api url."
            " Could be api key issue or api url issue.",
        ) from None

    return key
