# Backup and restore

**Owner role:** platform_engineering · **Introduced:** M8.4
**Source of truth:** masterplan section 20.4 (release gates), plan milestone
M8.4 Definition of done.

## What is backed up

The platform's durable state is the project record:

1. **OKF artifacts and Git history** — retained in the active-project
   repository and the two template repositories. Git remotes are the
   primary backup; a local working copy is never the only copy.
2. **Run/event database** — the SQLite (or PostgreSQL) database holding
   `run_state` and `events` (masterplan section 18.1). This is the
   append-only event stream and run state machine.

## Backup procedure

- A point-in-time backup is a compressed archive of the platform state
  directory (database file(s) plus any artifacts not yet pushed) with a
  SHA-256 checksum manifest embedded in the archive.
- Rehearsal script: `ops/rehearsal/dr_rehearsal.py`.

```text
python ops/rehearsal/dr_rehearsal.py \
  --source <platform-state-dir> \
  --backup-dir <backup-location> \
  --result-out ops/rehearsal/result.json
```

## Restore procedure

1. Extract the archive.
2. Verify every file against the embedded SHA-256 manifest (the script
   does this automatically and fails the rehearsal on any mismatch).
3. Point the platform at the restored database and re-run `mas migrate`
   and `mas index rebuild` to re-derive indexes from restored OKF files.

## Rehearsal record

The most recent rehearsal is recorded in
[`ops/rehearsal/result.json`](../rehearsal/result.json). The measured
numbers (backup/restore/verify durations and the data-loss window) come
from that actual run — no asserted numbers. Re-run the script and commit
the new `result.json` after any change to the backup/restore path.

## RPO / RTO statement

- **RPO (data-loss window):** the measured interval between the backup
  snapshot and a completed verified restore (see `result.json`). To
  reduce it, increase backup frequency.
- **RTO:** dominated by restore + verify duration (see `result.json`).

These values are rehearsal measurements on the vertical-slice state, not
production service-level guarantees.
