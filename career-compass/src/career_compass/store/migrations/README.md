Forward-only, numbered migrations: `001_initial.sql`, `002_....sql`.

Applied in order; the applied version is tracked in a `schema_version` table.
No down-migrations — with a version-controlled single-file database, the
rollback is `git checkout`.
