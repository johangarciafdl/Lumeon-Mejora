from services.assistant_workflow import AssistantSession, is_cancellation, is_confirmation


def test_write_action_requires_confirmation():
    session = AssistantSession()
    result = session.propose("create_customer", {"nombre": "Ana"})
    assert result["status"] == "confirmation_required"
    assert session.pending_intent == "create_customer"


def test_confirmation_consumes_pending_action():
    session = AssistantSession()
    session.propose("create_customer", {"nombre": "Ana"})
    assert session.confirm() == ("create_customer", {"nombre": "Ana"})
    assert session.confirm() is None


def test_cancel_clears_pending_action():
    session = AssistantSession()
    session.propose("create_customer", {"nombre": "Ana"})
    assert session.cancel() is True
    assert session.pending_intent is None


def test_confirmation_words_are_explicit():
    assert is_confirmation("sí")
    assert is_confirmation("CONFIRMAR")
    assert not is_confirmation("quizá")
    assert is_cancellation("cancelar")
