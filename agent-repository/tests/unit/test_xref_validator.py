from agent_platform.schemas.xref_validator import (
    DANGLING_REFERENCE,
    INCOMPATIBLE_RELATION_TYPE,
    validate_cross_references,
)


def test_valid_tree_has_no_xref_issues(fixtures_dir):
    result = validate_cross_references(fixtures_dir / "okf" / "valid")
    assert result.ok
    assert result.issues == []
    assert set(result.index) == {"EPIC-100", "US-100", "TC-100"}


def test_dangling_relation_target_detected(fixtures_dir):
    result = validate_cross_references(fixtures_dir / "okf" / "invalid_dangling")
    assert not result.ok
    assert any(issue.code == DANGLING_REFERENCE for issue in result.issues)


def test_incompatible_relation_target_type_detected(fixtures_dir):
    result = validate_cross_references(fixtures_dir / "okf" / "invalid_incompatible_type")
    assert not result.ok
    assert any(issue.code == INCOMPATIBLE_RELATION_TYPE for issue in result.issues)
