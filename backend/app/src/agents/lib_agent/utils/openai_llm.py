"""OpenAI ChatCompletion client wrapper with optional tool-calls."""

import os
from typing import Any, Optional, Union, Iterable, cast
from typing import Literal

from openai import OpenAI, NOT_GIVEN
from openai.types.chat import (
    ChatCompletionToolParam,
    ChatCompletionNamedToolChoiceParam,
)

from src.agents.lib_agent.base_llm import BaseLLM


class OpenAILLM(BaseLLM):
    """Wrapper around the OpenAI client to provide chat and complete methods."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None) -> None:
        """Initialize client with model name and API key from env by default."""
        self.model = model
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.use_open_router = os.getenv("USE_OPEN_ROUTER", "false").lower() == "true"
        if self.use_open_router:
            self.client = OpenAI(api_key=self._api_key, base_url="https://openrouter.ai/api/v1")
            self.model = "deepseek/deepseek-chat-v3.1:free"
        else:
            self.client = OpenAI(api_key=self._api_key)

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[Iterable[ChatCompletionToolParam]] = None,
        tool_choice: Optional[
            Union[Literal["none", "auto", "required"], ChatCompletionNamedToolChoiceParam]
        ] = None,
    ) -> dict[str, Any]:
        """Call chat completions and normalize output to content/tool_calls dict."""
        # Build explicit call for mypy compatibility; cast dynamic dicts to Any
        response = self.client.chat.completions.create(
            model=self.model,
            messages=cast(Any, messages),
            tools=tools if tools is not None else NOT_GIVEN,
            tool_choice=tool_choice if tool_choice is not None else NOT_GIVEN,
        )
        msg = response.choices[0].message
        out: dict[str, Any] = {"content": msg.content or ""}
        tool_calls = getattr(msg, "tool_calls", None) or []
        if tool_calls:
            out["tools_calls"] = [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in tool_calls
            ]
        return out

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[Iterable[ChatCompletionToolParam]] = None,
        tool_choice: Optional[
            Union[Literal["none", "auto", "required"], ChatCompletionNamedToolChoiceParam]
        ] = None,
    ) -> str:
        """Compatibility method returning only the content string."""
        out = self.chat(messages, tools=tools, tool_choice=tool_choice)
        return cast(str, out["content"])
