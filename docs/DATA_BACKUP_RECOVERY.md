# YOMA Data Backup & Recovery

## What to back up

Stop YOMA cleanly, then copy the SQLite database named by `YOMA_DATABASE_PATH` to a protected offline backup location. Separately back up the user-approved workspace directories using the operating system's trusted backup process. YOMA metadata and workspace files are distinct datasets.

## Restore

Stop YOMA, preserve the damaged database as a forensic copy, and replace the configured database with a trusted backup. Start YOMA and check `/readyz`, authentication, workspace-root metadata, conversations, memories, and audit records. Restore workspace files separately; database restoration does not recreate missing files.

## Reset

Stop YOMA, record the configured database path, and move only that SQLite file and its SQLite sidecar files to a protected archive or delete them after explicit pilot-user confirmation. Do not delete approved workspace directories. A fresh database requires bootstrap credentials and re-approval of workspace roots.

Do not upload backups automatically, include secrets in filenames or logs, or copy database files while YOMA is actively writing.
