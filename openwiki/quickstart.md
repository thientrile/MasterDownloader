---
type: Guide
title: MasterDownloader OpenWiki quickstart
description: Entry point for navigating MasterDownloader's PyQt desktop architecture, social download workflows, duplicate cleanup, and focused validation.
tags: [repository, quickstart, downloads, desktop-app]
openwiki:
  roles: [repository]
  source_paths: [App.py, MasterDownloader.py, requirements.txt]
---

# MasterDownloader OpenWiki quickstart

This wiki documents the current local Python desktop application. Start here to route a change, then use the linked page as the canonical home for behavior, source ownership, invariants, and narrow validation. Source code and tests remain authoritative; this wiki does not contain user credentials, cookies, sessions, or configuration values.

## What the repository contains

- [Desktop application architecture](architecture/desktop-application.md) covers the PyQt6 entry point, worker lifecycle, configuration, local state, credentials boundary, launchers, and Windows packaging.
- [Social media download workflows](workflows/social-downloads.md) covers TikTok, Instagram, and Facebook routing, gallery-dl/yt-dlp options, archives, cookies, and video/audio format policy.
- [Duplicate cleanup and deleted-file registry](workflows/duplicate-cleanup.md) covers content-based scan stages, review selection, deletion ordering, and the MD5 registry that flags reappearing files.

The application starts in `App.py`, where `MainWindow` creates `MasterDownloader` and dispatches work. That core in `MasterDownloader.py` performs both the download workflows and duplicate cleanup; the two branches share local state but have different persistence semantics.

## Task routing

| Change area or user intent | Relevant wiki page | Exact source entry points | Important symbols or types | Focused tests | Minimal validation command |
| --- | --- | --- | --- | --- | --- |
| Change queue behavior, worker signals, progress, row status, or concurrency | [Desktop application architecture](architecture/desktop-application.md) | `App.py`: `MainWindow.start_download`, `DownloadWorker.run`, `MainWindow.handle_progress`, `MainWindow.handle_finished`, `MainWindow.handle_error` | `MainWindow`, `DownloadWorker`, `WorkerSignals`, `QThreadPool` | No focused download-worker test exists | `./StartApp.sh` for a manual smoke check |
| Change launcher, GUI config, default folders, credentials, sessions, or packaging | [Desktop application architecture](architecture/desktop-application.md) | `StartApp.sh`, `StartApp.bat`, `build.bat`; `App.py`: `load_config`; `MasterDownloader.py`: `migrate_security`, `get_ig_session` | `MasterDownloader`, `migrate_security`, `get_manual_cookie`, `set_manual_cookie` | `tests/test_dedup_dialog.py` only covers a related PyQt dialog | `.venv/bin/python -m unittest -q tests/test_dedup_dialog.py` |
| Add or alter a TikTok URL type, gallery-dl option, cookie strategy, archive, or progress | [Social media download workflows](workflows/social-downloads.md) | `MasterDownloader.py`: `_tiktok_url_kind`, `download_tiktok`, `download_tiktok_photo`, `download_tiktok_story` | `_video_format`, `_prepare_yt_dlp`, `_create_temp_cookie_file` | `tests/test_social_media_download_options.py`, `tests/test_video_format.py` | `.venv/bin/python -m unittest -q tests/test_social_media_download_options.py tests/test_video_format.py` |
| Change Instagram or Facebook download options, supported links, video/audio behavior, or backend | [Social media download workflows](workflows/social-downloads.md) | `MasterDownloader.py`: `download_instagram_gallerydl`, `download_instagram`, `download_facebook` | `_instagram_url_kind`, `_video_format`, `_get_ffmpeg_exe` | `tests/test_social_media_download_options.py`, `tests/test_video_format.py` | `.venv/bin/python -m unittest -q tests/test_social_media_download_options.py tests/test_video_format.py` |
| Change media duplicate detection, deleted-file identity, dialog defaults, or file removal | [Duplicate cleanup and deleted-file registry](workflows/duplicate-cleanup.md) | `MasterDownloader.py`: `find_duplicates`, `delete_paths`; `App.py`: `DuplicateWorker.run`, `DuplicatesDialog`, `handle_scan_result` | `_quick_signature`, `_file_hash`, `_load_deleted_md5`, `_record_deleted_md5` | `tests/test_dedup_md5.py`, `tests/test_dedup_dialog.py` | `.venv/bin/python -m unittest -q tests/test_dedup_md5.py tests/test_dedup_dialog.py` |

Use `.venv/bin/python` when the repository virtual environment exists; `StartApp.sh` creates it on Linux/WSL when needed. The tests are `unittest` modules; `-q` keeps successful runs quiet while retaining failure diagnostics. Do not default to real social-network downloads or PyInstaller builds: run those only when the change crosses their respective integration or packaging boundary.

## Change approach

1. Follow the table to the canonical workflow page and start at its listed entry point.
2. Trace one hop into the desktop/core relationship where needed: UI dispatch is in `App.py`, business behavior is in `MasterDownloader.py`.
3. Preserve the page's explicit invariants, then run its focused test command.
4. Add a targeted test when changing a command option, identity rule, or externally visible selection default. Do not make generated output or user-specific runtime data the source of truth.

## Backlog

No evidence-blocked documentation areas are currently tracked.
