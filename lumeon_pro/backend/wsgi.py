"""WSGI entrypoint for the Lumeon Pro v2 deployment.

PythonAnywhere should point its Web app WSGI file at this module.
"""

from app_v2 import app

application = app
