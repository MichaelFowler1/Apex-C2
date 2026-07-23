"""Several source files have spaces in their names (range convention:
'physical pipeline.py'), so tests load them by path instead of import name.
krpc must be installed for the imports to resolve, but no KSP instance is
needed — tests exercise only the pure logic."""
import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_module(relpath, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, relpath))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
