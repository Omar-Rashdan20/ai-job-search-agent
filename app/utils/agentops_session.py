import json
from typing import Any

from app.config import AGENTOPS_API_KEY

_agentops = None
_session = None
_trace = None
_initialized = False
_active = False
_replay_url = ""


def _record_event(action_type: str, logs: dict[str, Any], returns: str = "") -> None:
    if _agentops is None:
        return

    try:
        from agentops import ActionEvent

        _agentops.record(
            ActionEvent(
                action_type=action_type,
                logs=json.dumps(logs, ensure_ascii=False),
                returns=returns,
            )
        )
    except Exception:
        return


def _capture_replay_url() -> str:
    if _trace is None:
        return ""

    try:
        from agentops.helpers.dashboard import get_trace_url

        return str(get_trace_url(_trace.span))
    except Exception:
        return ""


def start_agentops_session(inputs: dict[str, Any] | None = None) -> bool:
    """Start one app-level AgentOps trace. The replay URL is printed on shutdown."""
    global _agentops, _session, _trace, _initialized, _active, _replay_url

    if not AGENTOPS_API_KEY:
        return False

    if _active:
        return False

    try:
        import agentops
    except Exception:
        return False

    _agentops = agentops
    inputs = inputs or {}
    tags = [
        "job-search",
        f"country:{inputs.get('country', '') or 'runtime'}",
        f"work_mode:{inputs.get('work_mode', '') or 'runtime'}",
    ]

    try:
        if not _initialized:
            try:
                agentops.init(
                    AGENTOPS_API_KEY,
                    auto_start_session=False,
                    default_tags=tags,
                    trace_name="job-search",
                    skip_auto_end_session=True,
                    log_session_replay_url=False,
                )
            except TypeError:
                agentops.init(
                    AGENTOPS_API_KEY,
                    tags=tags,
                    skip_auto_end_session=True,
                )
            _initialized = True

        if hasattr(agentops, "start_trace"):
            try:
                _trace = agentops.start_trace("job-search", tags=tags)
            except TypeError:
                _trace = agentops.start_trace("job-search")
        elif hasattr(agentops, "start_session"):
            try:
                _session = agentops.start_session(tags=tags)
            except TypeError:
                _session = agentops.start_session()
        else:
            _session = None

        _active = True
        _replay_url = _capture_replay_url()
        _record_event(
            "Job search app started",
            {"app": "job-search"},
            "started",
        )
        return True
    except Exception:
        return False


def record_agentops_event(
    action_type: str, logs: dict[str, Any] | None = None, returns: str = ""
) -> None:
    _record_event(action_type, logs or {}, returns)


def end_agentops_session(success: bool, reason: str = "") -> None:
    """End the active AgentOps trace/session and print one replay URL."""
    global _session, _trace, _active, _replay_url
    if not _active or _agentops is None:
        return

    state = "Success" if success else "Failure"
    _record_event(
        "Job search app finished",
        {"success": success, "reason": reason},
        "finished" if success else reason,
    )

    try:
        if not _replay_url:
            _replay_url = _capture_replay_url()

        if _trace is not None and hasattr(_agentops, "end_trace"):
            try:
                _agentops.end_trace(_trace, end_state=state)
            except TypeError:
                try:
                    _agentops.end_trace(_trace, state)
                except TypeError:
                    _agentops.end_trace(end_state=state)
        elif _session is not None and hasattr(_session, "end_session"):
            try:
                _session.end_session(state, end_state_reason=reason)
            except TypeError:
                _session.end_session(state)
        elif hasattr(_agentops, "end_session"):
            try:
                _agentops.end_session(state, end_state_reason=reason)
            except TypeError:
                _agentops.end_session(state)
    except Exception:
        return
    finally:
        if _replay_url:
            print(
                f"\U0001F587 AgentOps: Session Replay for job-search trace: {_replay_url}",
                flush=True,
            )
        _active = False
        _session = None
        _trace = None
        _replay_url = ""
