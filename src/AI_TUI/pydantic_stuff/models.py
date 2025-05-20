# pylint: disable = C0116, C0115, C0114, C0411, E0213

from __future__ import annotations

from typing import Literal, cast, TypeAlias
from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator
from AI_TUI.pydantic_stuff.validators import (
    verify_endpoint,
    verify_api_key,
    get_models_list,
)

DEFAULT_API = cast(HttpUrl, "https://generativelanguage.googleapis.com/v1beta/")
ApiType: TypeAlias = Literal["google", "openai"]
StringBool: TypeAlias = Literal["yes", "no"]


class Config(BaseModel):
    # the defaults change via the TOML config
    api_key: str
    prompt: str = "You are a helpful assistant."
    overwrite_log: StringBool = "no"
    model: str = "gemini-2.5-flash-preview-04-17"
    api_type: ApiType = "google"
    endpoint: HttpUrl = DEFAULT_API
    model_config = ConfigDict(str_min_length=2, frozen=True)

    @field_validator("endpoint")
    def _(cls, v) -> HttpUrl:
        return verify_endpoint(v)
