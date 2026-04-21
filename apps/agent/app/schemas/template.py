from __future__ import annotations

from pydantic import BaseModel


class TemplateRenderResult(BaseModel):
    render_mode: str = "strict"
    rendered_text: str = ""
