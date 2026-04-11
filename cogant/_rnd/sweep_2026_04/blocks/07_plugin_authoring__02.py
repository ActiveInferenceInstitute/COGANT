# py/cogant/plugins/__init__.py

from cogant.plugins.python import PythonPlugin
from cogant.plugins.javascript import JavaScriptPlugin
from cogant.plugins.typescript import TypeScriptPlugin
from cogant.plugins.ruby import RubyPlugin

PLUGIN_REGISTRY = [
    PythonPlugin(),
    JavaScriptPlugin(),
    TypeScriptPlugin(),
    RubyPlugin(),  # <-- new
]
