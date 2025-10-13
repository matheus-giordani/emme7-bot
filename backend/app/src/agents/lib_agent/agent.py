"""Agent orchestrates LLM + tools with a simple function-calling loop."""

from typing import Any, Callable, Optional, Sequence, Tuple, get_type_hints
import json

from pydantic import ValidationError

from .agent_prompt_loader import AgentPromptLoader
from .base_context_providers import ContextProvider
from .base_llm import BaseLLM, EchoLLM
from .base_memory import Memory
from .message import Message
from .tool import ToolContext, ToolSpec


ROLE_TO_WHO = {"user": "usr", "assistant": "llm"}
WHO_TO_ROLE = {"usr": "user", "llm": "assistant"}


class Agent:
    """Encapsulates LLM, memory, tools and context providers."""

    def __init__(
        self,
        name: str,
        llm: Optional[BaseLLM] = None,
        memory: Optional[Memory] = None,
        tools: Optional[Sequence[Callable[..., Any]]] = None,
        context_providers: Optional[Sequence[ContextProvider]] = None,
    ):
        """Initialize the agent and register provided tools/context providers."""
        self.name = name
        self.system_prompt = AgentPromptLoader('./prompts').get_system_prompt(name)
        self.system_prompt = self.system_prompt.strip()
        self.llm = llm or EchoLLM()
        self.memory = memory or Memory()

        self.tool_specs: dict[str, ToolSpec] = {}
        self.context_providers: list[ContextProvider] = list(context_providers or [])
        if tools:
            for f in tools:
                self.add_tool(f)

    def add_tool(self, func: Callable[..., Any]) -> None:
        """Register a function marked with @tool decorator."""
        spec: ToolSpec = getattr(func, "_tool_spec", None)  # type: ignore
        if not spec:
            raise ValueError("Função não possui @tool")
        if spec.name in self.tool_specs:
            raise ValueError(f"Tool '{spec.name}' já registrada")
        self.tool_specs[spec.name] = spec

    def _openai_tools(self) -> list[dict[str, Any]]:
        """Render internal tool specs into OpenAI Chat tools payload."""
        out = []
        for spec in self.tool_specs.values():
            parameters = {"type": "object", "properties": {}, "required": []}
            if spec.schema:
                parameters = spec.schema.model_json_schema()
            out.append(
                {
                    "type": "function",
                    "function": {
                        "name": spec.name,
                        "description": spec.description,
                        "parameters": parameters,
                    },
                }
            )
        return out

    def _messages_for_llm(
        self, user_text: str, conversation_window: list[Message]
    ) -> list[dict[str, Any]]:
        """Build messages with system, context providers, history and current user text."""
        msgs: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        for provider in self.context_providers:
            msgs.extend(provider(self, user_text) or [])
        for m in conversation_window:
            if m.who_sent not in ("usr", "llm"):
                continue  # IGNORA tool/system do histórico
            msgs.append({"role": WHO_TO_ROLE.get(m.who_sent, ""), "content": m.content})

        # mensagem atual do usuário
        msgs.append(
            {"role": "user", "content": f"ultima mensagem do usuario:{user_text}"}
        )
        return msgs

    def _validate_and_call_tool(self, name: str, args_json: str) -> Tuple[str, str]:
        """Validate JSON args against schema (if any) and call the tool."""
        if name not in self.tool_specs:
            return name, f'Erro: tool "{name}" não registrada.'
        spec = self.tool_specs[name]
        try:
            args = json.loads(args_json or "{}")
        except json.JSONDecodeError:
            return name, "Erro ao decodificar argumentos JSON."
        if spec.schema:
            try:
                parsed = spec.schema(**args)
                args = parsed.model_dump()
            except ValidationError as ve:
                return name, f"Argumentos inválidos: {ve}"

        ctx = ToolContext(agent=self, memory=self.memory)

        # inspeciona assinatura da tool
        try:
            params = get_type_hints(spec.func)
            if any(p is ToolContext for p in params.values()):
                result = spec.func(args, ctx=ctx)  # injeta ctx
            else:
                result = spec.func(args)  # só args nomeados
        except TypeError as te:
            return name, f"Erro ao chamar tool: {te}"
        if isinstance(result, (dict, list)):
            return name, json.dumps(result, ensure_ascii=False)
        return name, str(result)

    def run(self, user_text: str, conversation_window: list[Message]) -> str:
        """Run the 2-pass loop with tool calls if the model requests them."""
        tools = self._openai_tools() if self.tool_specs else None
        msgs = self._messages_for_llm(user_text, conversation_window)
        reply = self.llm.chat(messages=msgs, tools=tools)

        tools_calls = reply.get("tools_calls") or []

        if tools_calls:
            tool_msgs_payload: list[dict[str, Any]] = []

            for tool_call in tools_calls:
                tname = tool_call["function"]["name"]
                args_json = tool_call["function"]["arguments"]
                _, output = self._validate_and_call_tool(tname, args_json)

                tool_msgs_payload.append(
                    {
                        "role": "tool",
                        "content": output,
                        "tool_call_id": tool_call["id"],  # <-- ESSENCIAL
                        "name": tname,  # opcional, mas ok
                    }
                )

            # segunda rodada
            msgs2 = list(msgs)
            msgs2.append(
                {
                    "role": "assistant",
                    "content": reply.get("content") or "",
                    "tool_calls": tools_calls,  # <-- ESSENCIAL
                }
            )
            msgs2.extend(tool_msgs_payload)

            final = self.llm.chat(messages=msgs2)
            content = str(final["content"])  # ensure str for strict typing
        else:
            content = str(reply["content"])  # ensure str for strict typing

        return content
