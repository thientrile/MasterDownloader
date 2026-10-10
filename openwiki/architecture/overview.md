---
type: architecture
title: Architecture Overview
description: How the PyQt6 desktop GUI in App.py drives the MasterDownloader core class, how work runs on a thread pool, and which local files hold configuration, history, credentials and archives.
tags: [architecture, gui, pyqt6, threading, state, security, packaging]
verified:
  - by: openwiki/0.6.0
    at: 2026-10-10T01:35:26.371Z
sources:
  - id: openwiki-source-ea70eb6c045047448e446296
    resource: repo://.gitignore
  - id: openwiki-source-54a3bad6602444acece2ba95
    resource: repo://App.py
  - id: openwiki-source-7dae91b469f36849f6b9156c
    resource: repo://build.bat
  - id: openwiki-source-a79b6a13ff60f59805b684fc
    resource: repo://MasterDownloader.py
generated: { by: "claude-code", at: "2026-10-10T01:35:26.371Z" }
---

# Architecture Overview

MasterDownloader is a single-process Python desktop tool for bulk-downloading
TikTok, Instagram and Facebook media and cleaning up duplicate files. It has two
modules:

| Module | Role |
|---|---|
| `App.py` | PyQt6 GUI (`MainWindow`), task table, settings, worker threads, duplicate dialog. |
| `MasterDownloader.py` | Core `MasterDownloader` class: platform downloaders, folder/history resolution, credential/cookie storage, duplicate scanning. Also runnable as an interactive console tool. |

## Entry points

- **GUI**: `App.py`'s `__main__` enables crash logging (`faulthandler` writing to
  `crash.log` next to the script), creates a `QApplication` with the Fusion style,
  checks that `yt_dlp` imports, then shows `MainWindow`.
- **Console**: `MasterDownloader.py`'s `__main__` calls `MasterDownloader().run()`,
  a prompt loop that dispatches by substring (`tiktok.com`, `facebook.com`,
  `instagram.com`). Only the console path calls `get_ig_session()` before an
  Instagram download.

## GUI to core

`MainWindow` owns exactly one `MasterDownloader` instance and one `QThreadPool`.
Its concurrency limit comes from `gui_config.json` key `max_concurrent`
(default 3) and is clamped to 1..16.

Adding a URL (`add_task`) resolves the platform and a target folder, appends a
row to the task table, persists the URL/folder into `saved_links`, and starts a
download. `start_download` maps the platform to `download_instagram`,
`download_tiktok` or `download_facebook` and wraps it in a `DownloadWorker`
(`QRunnable`). The worker injects a `progress_callback` keyword so the core can
report `(percent, message)` without knowing about Qt; it is re-emitted as the
`progress` signal tagged with the table row id.

Signals (`WorkerSignals`): `progress`, `result`, `error`, `finished`. Errors
mark the row as failed so the subsequent `finished` signal does not overwrite
the status with "Completed". The duplicate scan uses a separate
`DuplicateWorker` that emits progress with `row_id = -1`, which `handle_progress`
routes to the status bar instead of a table row.

Rows are addressed by their table index; the code assumes the table is
append-only while workers run.

## Local state

All state is relative to `base_dir` (the script folder, or the executable folder
when frozen by PyInstaller):

| Path | Owner | Content |
|---|---|---|
| `gui_config.json` | GUI | download folder, `saved_links`, `default_download_folder`, `max_concurrent` |
| `history.json` | core | username to folder mapping used by `resolve_folder` |
| `ig_credentials.txt` | core | Instagram username/password, Fernet-encrypted |
| `cookies.json` | core | per-platform manual cookie strings, Fernet-encrypted |
| `secret.key` | core | Fernet key used for the two files above |
| `sessions/` | core | Instaloader session files |
| `archives/` | core | legacy archives and the global `deleted_md5.txt` registry |

`.gitignore` excludes the config, history, credential, cookie, session and
archive paths. **`secret.key` is not ignored and is tracked in Git**, so anyone
with the repository can decrypt credential and cookie files created with that
key. Rotate or untrack it before sharing the repository.

### Credential encryption

`_load_crypto_key` loads `secret.key` or generates a new key (silently
continuing if it cannot be written). On startup `migrate_security` re-encrypts
any plaintext credentials or cookie values (detected by the absence of the
`gAAAA` Fernet prefix). Decryption failures fall back to returning the input,
so plaintext values still load.

### Legacy migration

`migrate_archives` moves old per-folder `downloaded.txt` yt-dlp archives into
`archives/` under `tiktok_<user>.txt` / `facebook_<user>.txt`; downloaders later
merge those into per-folder archive files (see
[Platform Download Pipelines](../workflows/platform-downloads.md)).

## Packaging and launchers

- `StartApp.sh` creates/uses `.venv`, installs `requirements.txt`
  (upgrading when `UPDATE_LIBS=1`), selects a Qt platform under WSL, and runs
  `App.py`. `StartApp.bat` runs `App.py` with the venv Python when present.
- `UpdateLibs.sh` upgrades every dependency and runs `pip check`.
- `build.bat` produces a PyInstaller one-dir windowed build named
  `MasterDownloader` and bundles local config/credential/session files into it,
  so a build made on a configured machine ships that machine's data.

## Related

- [Platform Download Pipelines](../workflows/platform-downloads.md)
- [Duplicate Cleanup and MD5 Registry](../workflows/duplicate-cleanup.md)
- [Quickstart](../quickstart.md)
