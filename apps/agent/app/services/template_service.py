"""Template renderer for formal soil warning text.

This service owns Jinja2 template rendering only.  It does not decide whether a
warning should be issued; that decision is already made by the rule engine.
Keeping rendering separate makes strict template tests easier to reason about.
"""

from __future__ import annotations


from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from app.repositories.soil_repository import SoilRepository


class TemplateService:
    """Render standard answer templates through a Jinja2 environment."""

    def __init__(self, repository: SoilRepository):
        """Prepare template environment; repository is kept for future lookups."""
        self.repository = repository
        self.template_env = Environment(
            loader=FileSystemLoader(str(Path(__file__).resolve().parents[1] / "templates")),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, *, answer_type: str, query_result: dict[str, Any], rule_result: dict[str, Any], slots: dict[str, Any]) -> dict[str, Any]:
        """Render warning text and choose whether advice should run afterward."""
        del answer_type
        records = rule_result.get("evaluated_records") or query_result.get("records") or []
        route_action = "go_advice" if rule_result.get("route_action") == "template_and_advice" else "go_response"
        if not records:
            # Empty records still preserve the route action so the Flow can
            # continue to response generation with a safe empty-data answer.
            return {
                "route_action": route_action,
                "rendered_text": "",
                "render_mode": slots.get("render_mode", "strict"),
            }
        record = records[0]
        render_mode = slots.get("render_mode", "strict")
        warning_label = record.get("display_label", "未达到预警条件")
        template = self.template_env.get_template("soil_warning.j2")
        rendered = template.render(
            year=str(record["create_time"])[:4],
            month=str(record["create_time"])[5:7],
            day=str(record["create_time"])[8:10],
            hour=str(record["create_time"])[11:13] or "00",
            city=record.get("city") or "",
            county=record.get("county") or "",
            sn=record.get("sn") or "",
            water20cm=record.get("water20cm") or "暂无",
            warning_level=warning_label,
        )
        if record.get("soil_status") == "not_triggered":
            # Strict templates must not pretend an official warning exists when
            # the deterministic rule result says the threshold was not reached.
            rendered = f"{rendered} 当前记录未达到正式预警条件。"
        return {
            "route_action": route_action,
            "rendered_text": rendered,
            "render_mode": render_mode,
        }


__all__ = ["TemplateService"]
