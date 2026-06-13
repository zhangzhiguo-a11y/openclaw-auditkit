from openclaw_auditkit.policy import classify_paths


def test_docs_are_a_class():
    result = classify_paths(["docs/readme.md"])
    assert result.risk_class == "A"
    assert result.apply_allowed is True


def test_source_is_b_class():
    result = classify_paths(["src/workflow.py"])
    assert result.risk_class == "B"
    assert result.requires_closeout_receipt is True


def test_secret_path_is_c_class():
    result = classify_paths(["config/secrets/api-token.txt"])
    assert result.risk_class == "C"
    assert result.apply_allowed is False

