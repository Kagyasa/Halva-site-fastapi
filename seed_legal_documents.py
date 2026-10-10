"""Compatibility entry point. No legal templates are published automatically."""

import sys

from app.cli import main

if __name__ == "__main__":
    main(["publish-legal", *sys.argv[1:]])
