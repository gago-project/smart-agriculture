from __future__ import annotations

"""Base class shared by all restricted Flow nodes."""

from dataclasses import dataclass

from app.schemas.state import NodeResult


@dataclass
class BaseNode:
    """Declare node name, allowed actions, and allowed state patch fields."""

    name: str
    allowed_next_actions: tuple[str, ...]
    allowed_patch_fields: tuple[str, ...]

    def ensure_result(self, result: NodeResult) -> NodeResult:
        """Validate a node result before the runner merges it into state."""
        if result.next_action not in self.allowed_next_actions:
            raise ValueError(f"Node {self.name!r} returned illegal next_action {result.next_action!r}")
        for field in result.state_patch:
            if field not in self.allowed_patch_fields:
                raise ValueError(f"Node {self.name!r} is not allowed to patch field {field!r}")
        return result
