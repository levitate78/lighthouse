import extensions


def test_extensions_are_instantiated():
    assert extensions.db is not None
    assert extensions.scheduler is not None
    assert extensions.login_manager is not None
    assert extensions.limiter is not None
    assert extensions.cors is not None
