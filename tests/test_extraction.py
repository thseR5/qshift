from qshift.agent.extraction import MockLLM, MockTranscriber, normalize_units


def test_telugu_english_request_creates_remove_and_replacement():
    ops = MockLLM().extract(
        "Kitchen lo granite badulu quartz pettandi, bedroom false ceiling remove cheyyandi."
    )
    assert [op["op"] for op in ops] == ["REMOVE", "REPLACE"]
    assert ops[1]["status"] == "NEEDS_INFO"


def test_voice_fixture_requires_confirmation():
    transcript = MockTranscriber().transcribe("telugu_quartz_change")
    assert transcript["requires_confirmation"] == "true"


def test_unit_normalization():
    assert normalize_units("120 square feet and 8 running feet") == "120 sqft and 8 rft"
