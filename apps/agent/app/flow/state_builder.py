from __future__ import annotations

"""Factory helpers for constructing a fresh `FlowState`.

Every chat request starts from a clean state object.  Keeping construction in a
single module makes tests and API handlers use the same defaults for request
IDs, trace IDs, channel, timezone, and normalized input text.
"""

import uuid

from app.schemas.state import FlowState


def build_flow_state(
    *,
    user_input: str,
    session_id: str,
    turn_id: int,
    request_id: str | None = None,
    trace_id: str | None = None,
    channel: str = "web",
    timezone: str = "Asia/Shanghai",
) -> FlowState:
    """Create the initial state passed to the Flow runner.

    `request_id` is externally visible and useful for API callers.  `trace_id`
    groups internal node snapshots.  They are separate on purpose: a caller can
    provide a request ID while the agent still owns its internal trace lineage.
    """
    return FlowState(
        request_id=request_id or str(uuid.uuid4()),
        trace_id=trace_id or str(uuid.uuid4()),
        session_id=session_id,
        turn_id=turn_id,
        user_input=user_input.strip(),
        channel=channel,
        timezone=timezone,
    )
