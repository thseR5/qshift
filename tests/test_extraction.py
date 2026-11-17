import json

import pytest

from qshift.agent.extraction import (
    ChangeExtraction,
    LocalModelUnavailable,
    MockLLM,
    MockTranscriber,
    OllamaChangeLLM,
    get_change_extractor,
    normalize_units,
)


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


def test_change_extractor_provider_is_configurable(monkeypatch):
    assert isinstance(get_change_extractor("mock"), MockLLM)
    assert isinstance(get_change_extractor("ollama"), OllamaChangeLLM)
    with pytest.raises(ValueError):
        get_change_extractor("unknown")


def test_ollama_change_response_is_schema_validated(monkeypatch):
    payload = {
        "message": {
            "content": json.dumps(
                {
                    "intent": "REMOVE",
                    "operations": [
                        {
                            "op": "REMOVE",
                            "room": "Guest Bedroom",
                            "target_text": "false ceiling",
                            "source_span": "remove the false ceiling",
                            "confidence": 0.9,
                            "status": "PROPOSED",
                        }
                    ],
                    "clarification": None,
                    "notes": [],
                }
            )
        }
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(payload).encode()

    monkeypatch.setattr(
        "qshift.agent.extraction.build_opener",
        lambda *_args, **_kwargs: type("Opener", (), {"open": lambda *_args, **_kwargs: Response()})(),
    )
    result = OllamaChangeLLM().extract("remove the false ceiling", {})
    assert isinstance(result, ChangeExtraction)
    assert result.operations[0].op == "REMOVE"


def test_ollama_unavailable_is_safe_error(monkeypatch):
    def fail(*_args, **_kwargs):
        raise OSError("offline")

    monkeypatch.setattr("qshift.agent.extraction.build_opener", fail)
    with pytest.raises(LocalModelUnavailable, match="Ollama is unavailable"):
        OllamaChangeLLM().extract("remove the ceiling", {})
