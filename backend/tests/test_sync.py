from sync import _parse_dt


def test_parse_dt_valid_timestamp():
    result = _parse_dt("2024-01-01T12:00:00Z")
    assert result is not None
    assert result.isoformat().startswith("2024-01-01T12:00:00")


def test_parse_dt_invalid_timestamp():
    assert _parse_dt("not-a-timestamp") is None
    assert _parse_dt(None) is None
