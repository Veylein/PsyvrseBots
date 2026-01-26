"""Minimal compatibility shim for Villicus `core` package.

This provides a tiny `config` module expected by the existing bot code so
the repo can run without the original monolithic package. It's intentionally
small — you can replace with the full implementation later.
"""

__all__ = ['config']
