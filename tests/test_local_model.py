from qshift.agent.local_model import Fact, client_source, validate_fact


def test_measurement_must_match_client_evidence_and_question() -> None:
    messages = [
        {"role": "assistant", "field": "height_ft"},
        {"role": "client", "text": "7 feet."},
    ]
    evidence = Fact(source=2, value="7", evidence="7 feet")
    assert validate_fact("height_ft", evidence, messages, messages[1]) == "7"
    assert validate_fact("width_ft", evidence, messages, messages[1]) is None
    guessed = Fact(source=2, value="10", evidence="7 feet")
    assert validate_fact("height_ft", guessed, messages, messages[1]) is None


def test_unique_client_evidence_resolves_incorrect_model_citation() -> None:
    messages = [
        {"role": "assistant", "text": "Can you confirm white laminate?"},
        {"role": "client", "text": "White laminate please."},
    ]
    fact = Fact(source=1, value="White laminate", evidence="white laminate")
    assert client_source(fact, messages) == 2
    assert client_source(fact, messages[:1]) is None
    assert client_source(fact, [*messages, messages[1]]) is None
