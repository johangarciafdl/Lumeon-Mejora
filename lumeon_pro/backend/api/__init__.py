"""HTTP/API layer for Lumeon V2."""

from .assistant_api import assistant_api
from .auth_api import auth_api
from .customer_api import customer_api
from .delivery_api import delivery_api
from .inventory_api import inventory_api
from .invoice_api import invoice_api
from .product_api import product_api
from .system_api import system_api


def register_blueprints(app):
    app.register_blueprint(assistant_api)
    app.register_blueprint(auth_api)
    app.register_blueprint(customer_api)
    app.register_blueprint(delivery_api)
    app.register_blueprint(inventory_api)
    app.register_blueprint(invoice_api)
    app.register_blueprint(product_api)
    app.register_blueprint(system_api)
