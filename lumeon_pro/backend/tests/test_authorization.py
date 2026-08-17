from services.authorization_service import Actor, can, require


def test_admin_has_write_and_admin_actions():
    actor = Actor(id=1, role="admin")
    assert can(actor, "create_sale")
    assert can(actor, "manage_users")


def test_vendedor_cannot_manage_users():
    actor = Actor(id=2, role="vendedor")
    assert can(actor, "create_sale")
    assert not can(actor, "manage_users")


def test_unknown_role_is_read_only():
    actor = Actor(id=3, role="unknown")
    assert can(actor, "search_customer")
    assert not can(actor, "create_customer")


def test_require_rejects_forbidden_action():
    actor = Actor(id=2, role="vendedor")
    try:
        require(actor, "delete_product")
    except PermissionError:
        return
    raise AssertionError("Expected PermissionError")
