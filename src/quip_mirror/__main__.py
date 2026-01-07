"""
Entry point for running quip_mirror as a module.

This allows the package to be run with: python -m quip_mirror
"""

from .cli import main

if __name__ == "__main__":
    main()