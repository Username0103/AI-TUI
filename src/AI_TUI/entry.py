# pylint: disable = C0116, C0115, C0114, C0411

import argparse
from AI_TUI.main import startup
from AI_TUI.main import ArgsSingleton


def main() -> None:
    """
    entry point for application for main.py
    optional, running main.py also works
    """

    parser = argparse.ArgumentParser(
        prog="AI-TUI",
        description="Allows users to use both the gemini and openai "
        "APIs in a nice and user-friendly terminal UI way.\n"
        "Includes free cake.",
        epilog="So Long, and Thanks for All the Fish!",
        argument_default=False,
    )
    parser.add_argument(
        "-s",
        "--skip",
        action="store_true",
        help="skip the tutorial about key-binds at the beginning",
    )
    parser.add_argument(
        "-o",
        "--options",
        action="store_true",
        help="see the options straight from the get-go",
    )

    args = parser.parse_args()
    ArgsSingleton.start_on_options = args.options
    ArgsSingleton.skip_intro = args.skip

    startup()


if __name__ == "__main__":
    main()
