"""HTTP/API layer for Lumeon V2."""

from .assistant_api import assistant_api
from .system_api import system_api


def register_blueprints(app):
    app.register_blueprint(assistant_api)
    app.register_blueprint(system_api)
