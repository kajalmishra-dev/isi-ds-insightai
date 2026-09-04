from backend.services.ingestion import should_flag_for_review


def test_low_confidence_without_alts_needs_review(monkeypatch):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.32")
    monkeypatch.setenv("CONFIDENCE_MARGIN", "0.10")
    import backend.core.config as config_module

    config_module.get_settings.cache_clear()
    # Reload settings singleton used by ingestion
    import backend.services.ingestion as ingestion

    ingestion.settings = config_module.get_settings()

    assert should_flag_for_review(0.20, []) is True
    assert should_flag_for_review(0.80, []) is False


def test_clear_margin_skips_review_even_if_soft(monkeypatch):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.32")
    monkeypatch.setenv("CONFIDENCE_MARGIN", "0.10")
    import backend.core.config as config_module
    import backend.services.ingestion as ingestion

    config_module.get_settings.cache_clear()
    ingestion.settings = config_module.get_settings()

    # Soft max-prob but clear winner vs runner-up
    assert (
        should_flag_for_review(
            0.28,
            [{"category": "service", "confidence": 0.10}],
        )
        is False
    )
    # Soft + ambiguous → review
    assert (
        should_flag_for_review(
            0.28,
            [{"category": "service", "confidence": 0.24}],
        )
        is True
    )
