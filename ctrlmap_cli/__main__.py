from __future__ import annotations

import sys

from ctrlmap_cli.cli import main as cli_main
from ctrlmap_cli.exceptions import CtrlMapError


def main() -> None:
    try:
        cli_main()
    except CtrlMapError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        sys.exit(130)


if __name__ == "__main__":
    main()
