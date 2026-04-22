"""Schema definitions for template within the soil agent."""

from __future__ import annotations

from pydantic import BaseModel


class TemplateRenderResult(BaseModel):
    """Schema describing the result of template rendering."""
    render_mode: str = "strict"
    rendered_text: str = ""
