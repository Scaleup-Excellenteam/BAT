"""Entry point: builds the sentence index and starts the CLI."""

import sys

import data_manager
from cli.main import run_cli


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python main.py <path-to-sentences-directory>")
        sys.exit(1)

    root_dir = sys.argv[1]
    data_manager.build_index(root_dir)
    run_cli()


if __name__ == "__main__":
    main()
