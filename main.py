from ui.gradio_app import build_ui


def main():
    app = build_ui()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=True,
    )


if __name__ == "__main__":
    main()
