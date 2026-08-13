#!/usr/bin/env python3
"""
E.V. API token generator.
Usage:
    python scripts/generate_token.py            # print new token
    python scripts/generate_token.py --write    # write to .env file
    python scripts/generate_token.py --rotate   # replace existing token in .env
"""
from __future__ import annotations

import argparse
import os
import re
import secrets
import string
from pathlib import Path


def generate_token(length: int = 48) -> str:
    """Generate a cryptographically secure URL-safe token."""
    alphabet = string.ascii_letters + string.digits + "-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> int:
    parser = argparse.ArgumentParser(description="E.V. API token generator")
    parser.add_argument("--write", action="store_true", help="Append token to .env")
    parser.add_argument("--rotate", action="store_true", help="Replace existing token in .env")
    parser.add_argument("--length", type=int, default=48, help="Token length (default 48)")
    args = parser.parse_args()

    token = generate_token(args.length)
    env_path = Path(__file__).parent.parent / ".env"

    if args.rotate and env_path.exists():
        src = env_path.read_text(encoding="utf-8")
        new = re.sub(
            r"^(JARVIS_API_TOKEN\s*=\s*).*$",
            f"\\g<1>{token}",
            src,
            flags=re.MULTILINE,
        )
        if new == src:
            # Key not found — append
            new = src.rstrip() + f"\nJARVIS_API_TOKEN={token}\n"
        env_path.write_text(new, encoding="utf-8")
        print(f"Token rotated in {env_path}")
    elif args.write:
        with env_path.open("a", encoding="utf-8") as f:
            f.write(f"\nJARVIS_API_TOKEN={token}\n")
        print(f"Token written to {env_path}")
    else:
        print(token)
        print()
        print("To use:")
        print(f"  echo 'JARVIS_API_TOKEN={token}' >> .env")
        print(f"  # or: python scripts/generate_token.py --write")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
