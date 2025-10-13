"""Base LLM interfaces used by the Agent with an Echo implementation."""

from typing import Any, Dict, List, Optional


class BaseLLM:
    """Abstract base class for chat/complete-compatible LLMs."""

    def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> str:
        """
        Gera uma resposta textual a partir de um histórico de mensagens no formato de chat.

        Args:
            messages (List[Dict[str, str]]): Lista de mensagens anteriores no formato
                [{"role": "user"|"assistant"|"system"|"tool", "content": "..."}].
            tools (Optional[List[Dict[str, Any]]]): Lista de ferramentas disponíveis para o modelo
                (em formato compatível com a API da OpenAI). Usada para habilitar chamadas de função.
            tool_choice (Optional[str]): Nome de uma ferramenta específica que o modelo deve usar
                obrigatoriamente, se aplicável.

        Returns:
            str: Texto gerado pelo modelo de linguagem, representando a resposta do assistente.

        Objetivo:
            Essa função encapsula a chamada de inferência ao modelo de linguagem (LLM), permitindo
            que diferentes implementações (OpenAI, EchoLLM, outros provedores) ofereçam uma
            interface consistente para gerar respostas em um contexto de conversa.
        """
        raise NotImplementedError

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retorna um dicionário no formato aproximado do OpenAI ChatCompletion com tool_calls."""
        # Implementações podem sobrescrever; por padrão usa complete() sem tool-calls
        content = self.complete(messages, tools=tools, tool_choice=tool_choice)
        return {"content": content, "tool_calls": []}


class EchoLLM(BaseLLM):
    """LLM de teste (não chama APIs)."""

    def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> str:
        """Echo the last user message to simulate an LLM response."""
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        return f"[EchoLLM] Você disse: {last_user}"
