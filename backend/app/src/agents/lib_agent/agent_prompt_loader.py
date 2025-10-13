"""Load agent prompts from TOML files for system messages."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import tomli as toml


class AgentPromptLoader:
    """Helper to resolve and load system_prompt for a given agent name."""

    def __init__(self, base_dir: str = "prompts") -> None:
        """Initialize loader using a base directory for prompts."""
        base_path = (Path(__file__).resolve().parent.parent / "prompts").resolve()
        self.base: Path = base_path
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _path_for(self, agent_name: str) -> Path:
        """Return the TOML file path for the given agent name."""
        return self.base / f"{agent_name}_prompt.toml"

    def _load(self, agent_name: str) -> Dict[str, Any]:
        """Read and parse the TOML prompt file for an agent."""
        path = self._path_for(agent_name)
        if not path.exists():
            # ajuda no diagnóstico mostrando o CWD também
            raise FileNotFoundError(
                f"Prompt file não encontrado: {path} (cwd={Path.cwd()})"
            )
        with path.open("rb") as f:
            return toml.load(f)  # type: ignore[no-any-return]

    def get_system_prompt(self, agent_name: str) -> str:
        """Return the system prompt string loaded from TOML for the agent."""
        data = self._load(agent_name)
        # ajuste a chave conforme seu TOML (ex.: "system" ou "system_prompt")
        return data.get("system") or data.get("system_prompt") or ""
