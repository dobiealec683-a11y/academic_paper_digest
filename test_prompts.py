from prompts import (
    FINANCE_DAILY_PROMPTS,
    PROMPT_FINANCE_EXECUTIVE_DIGEST,
    PROMPT_FINANCE_PAPER_SYNTHESIS,
)


def test_finance_daily_prompts_map_to_expected_export_suffixes() -> None:
    suffixes = [suffix for _, suffix in FINANCE_DAILY_PROMPTS]

    assert suffixes == ["extraction", "synthesis", "digest", "map"]


def test_finance_digest_prompt_is_phone_friendly_and_single_paper() -> None:
    assert "single finance paper" in PROMPT_FINANCE_EXECUTIVE_DIGEST
    assert "Keep the whole brief phone-friendly" in PROMPT_FINANCE_EXECUTIVE_DIGEST
    assert "The One Big Idea" in PROMPT_FINANCE_EXECUTIVE_DIGEST


def test_finance_synthesis_prompt_prevents_outside_facts() -> None:
    assert "Use only the uploaded sources" in PROMPT_FINANCE_PAPER_SYNTHESIS
    assert "Do not introduce outside facts" in PROMPT_FINANCE_PAPER_SYNTHESIS
    assert "every point, every counterpoint, every argument" in PROMPT_FINANCE_PAPER_SYNTHESIS
    assert "college finance student" in PROMPT_FINANCE_PAPER_SYNTHESIS
    assert "quasi-narrative" in PROMPT_FINANCE_PAPER_SYNTHESIS
