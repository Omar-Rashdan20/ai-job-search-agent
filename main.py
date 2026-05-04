from ui.gradio_app import build_ui
from app.utils.agentops_session import end_agentops_session, start_agentops_session


def main():
    app = build_ui()
    agentops_started = start_agentops_session()
    success = True
    reason = ""

    try:
        app.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=True,
        )
    except KeyboardInterrupt:
        reason = "Server stopped by user."
    except Exception as exc:
        success = False
        reason = str(exc)
        raise
    finally:
        if agentops_started:
            end_agentops_session(success, reason)


if __name__ == "__main__":
    main()
