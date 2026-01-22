"""
Package initializer for villicus.

This file ensures that code which imports the top-level `core` package
(`from core import ...` or `from core.config import ...`) will resolve to
the `villicus.core` modules contained in this repository. That allows the
existing codebase to remain unchanged while keeping everything inside the
`villicus/` folder for publishing.
"""
import importlib
import sys

try:
    # Import villicus.core (it is inside this package) and register it as
    # the top-level `core` module so `import core` and `from core.*` work.
    core_mod = importlib.import_module('villicus.core')
    sys.modules.setdefault('core', core_mod)
except Exception:
    # If import fails (early import before files exist), ignore — the
    # same resolution will be attempted when `villicus.core` becomes
    # importable.
    pass
