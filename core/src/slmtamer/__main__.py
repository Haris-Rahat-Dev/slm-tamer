import argparse

import uvicorn

from . import config


def main() -> None:
    parser = argparse.ArgumentParser(prog="slmtamer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    config.ensure_dirs()
    uvicorn.run("slmtamer.api.app:app", host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
