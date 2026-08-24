from agent_platform.migrations.runner import (
    applied_migrations,
    discover_migrations,
    run_pending_migrations,
)


def test_discover_migrations_finds_initial():
    migrations = discover_migrations()
    keys = [m.key for m in migrations]
    assert "0001_initial" in keys
    # Ordered by ascending numeric prefix.
    assert keys == sorted(keys)


def test_run_pending_migrations_is_idempotent(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    first_run = run_pending_migrations(project_dir)
    assert first_run == ["0001_initial"]
    assert "0001_initial" in applied_migrations(project_dir)

    second_run = run_pending_migrations(project_dir)
    assert second_run == []  # nothing new to apply
