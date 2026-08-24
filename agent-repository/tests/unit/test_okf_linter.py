from pathlib import Path

from agent_platform.schemas.okf_linter import (
    MISSING_TEST_CASE_REF,
    SCHEMA_ERROR,
    UNTESTED_USER_STORY,
    SchemaRegistry,
    lint_directory,
)


def test_valid_tree_lints_clean(schema_dir, fixtures_dir):
    registry = SchemaRegistry(schema_dir)
    result = lint_directory(fixtures_dir / "okf" / "valid", registry)
    assert result.errors == []
    assert result.ok


def test_missing_required_field_is_schema_error(schema_dir, fixtures_dir):
    registry = SchemaRegistry(schema_dir)
    result = lint_directory(fixtures_dir / "okf" / "invalid_schema", registry)
    assert not result.ok
    assert any(issue.code == SCHEMA_ERROR for issue in result.errors)


def test_untested_user_story_flagged_with_specific_code(schema_dir, fixtures_dir):
    registry = SchemaRegistry(schema_dir)
    result = lint_directory(fixtures_dir / "okf" / "invalid_untested_story", registry)
    assert not result.ok
    codes = {issue.code for issue in result.errors}
    assert UNTESTED_USER_STORY in codes


def test_valid_spoc_round_trips_schema(schema_dir, fixtures_dir):
    registry = SchemaRegistry(schema_dir)
    result = lint_directory(fixtures_dir / "spoc", registry)
    # The "missing test case refs" fixture only produces a warning, not an error.
    assert result.ok


def test_spoc_missing_test_case_refs_is_a_warning_not_an_error(schema_dir, fixtures_dir):
    registry = SchemaRegistry(schema_dir)
    result = lint_directory(fixtures_dir / "spoc", registry)
    warning_codes = {issue.code for issue in result.warnings}
    assert MISSING_TEST_CASE_REF in warning_codes
    assert all(
        issue.severity == "warning"
        for issue in result.issues
        if issue.code == MISSING_TEST_CASE_REF
    )
