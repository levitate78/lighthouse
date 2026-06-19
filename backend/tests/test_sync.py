from sync import _extract_test_summary, _parse_dt


def test_parse_dt_valid_timestamp():
    result = _parse_dt("2024-01-01T12:00:00Z")
    assert result is not None
    assert result.isoformat().startswith("2024-01-01T12:00:00")


def test_parse_dt_invalid_timestamp():
    assert _parse_dt("not-a-timestamp") is None
    assert _parse_dt(None) is None


def test_extract_test_summary_maps_gitlab_total_fields():
    summary = _extract_test_summary(
        {
            "total": {
                "count": 6,
                "success": 4,
                "failed": 1,
                "skipped": 1,
                "error": 0,
                "time": 12.5,
            }
        }
    )

    assert summary == {
        "test_total": 6,
        "test_success": 4,
        "test_failed": 1,
        "test_skipped": 1,
        "test_error": 0,
        "test_duration": 12.5,
    }
