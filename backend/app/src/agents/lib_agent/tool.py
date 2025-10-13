"""Tool registration utilities for the Agent function-calling system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING, TypeVar, Union

from pydantic import BaseModel

if TYPE_CHECKING:  # only for static typing; avoids runtime circular imports
    from .agent import Agent
    from .base_memory import Memory


@dataclass
class ToolSpec:
    """Specification describing a registered tool."""

    name: str
    description: str
    schema: Optional[type[BaseModel]]
    func: Callable[..., Union[str, Dict[str, Any]]]


@dataclass
class ToolContext:
    """Context passed to tools that request it (agent + memory)."""

    agent: "Agent"
    memory: "Memory"


F = TypeVar("F", bound=Callable[..., Any])


def tool(
    name: str, description: str, schema: Optional[type[BaseModel]] = None
) -> Callable[[F], F]:
    """Register a function as a Tool via decorator."""

    def decorator(func: F) -> F:
        spec = ToolSpec(name=name, description=description, schema=schema, func=func)
        setattr(func, "_tool_spec", spec)
        return func

    return decorator
