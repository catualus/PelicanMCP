import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(repo_root))

    from pelican_mcp.server import main as server_main

    server_main()


if __name__ == "__main__":
    main()
