---
type: quickstart
title: Quickstart
description: What MasterDownloader is, how to run, update, build and test it, and which wiki page to open for each kind of task.
tags: [quickstart, setup, testing, navigation]
verified:
  - by: openwiki/0.6.0
    at: 2026-10-10T01:35:26.371Z
sources:
  - id: openwiki-source-a79b6a13ff60f59805b684fc
    resource: repo://MasterDownloader.py
  - id: openwiki-source-373640cd8a0886cee69db282
    resource: repo://requirements.txt
  - id: openwiki-source-eef604eb1228cd055d5146b6
    resource: repo://StartApp.sh
  - id: openwiki-source-325376993cc5382017cdb9f7
    resource: repo://tests/test_dedup_dialog.py
  - id: openwiki-source-6c548cfebdee31c60af068cf
    resource: repo://tests/test_dedup_md5.py
  - id: openwiki-source-aaea14acbbe01ca9941ad6b8
    resource: repo://UpdateLibs.sh
generated: { by: "claude-code", at: "2026-10-10T01:35:26.371Z" }
---

# Quickstart

MasterDownloader is a Python desktop app (PyQt6) that bulk-downloads media from
TikTok, Instagram and Facebook and removes content-duplicate images and videos.
The GUI lives in `App.py`; all download and dedup logic lives in the
`MasterDownloader` class in `MasterDownloader.py`, which can also run as a
console prompt.

## Run

| Platform | Command | Notes |
|---|---|---|
| Linux / WSL | `./StartApp.sh` | Creates `.venv` if missing, installs `requirements.txt`, picks a Qt backend under WSL, runs `App.py`. `UPDATE_LIBS=1` upgrades dependencies first. |
| Windows | `StartApp.bat` | Uses `.venv\Scripts\python.exe` when present. |
| Console mode | `python MasterDownloader.py` | Prompt loop; asks for Instagram login if no session/cookie is available. |

Main dependencies (`requirements.txt`): `yt-dlp`, `gallery-dl`, `instaloader`,
`PyQt6`, `cryptography`, `browser-cookie3`, `imageio-ffmpeg`, `Pillow`,
`imagehash`, `requests`. ffmpeg comes from `PATH` or `imageio-ffmpeg`.

## Update dependencies

`./UpdateLibs.sh` upgrades pip and every requirement inside `.venv`, then runs
`pip check` and lists outdated packages. Platform breakage is usually fixed by
upgrading `yt-dlp` / `gallery-dl`.

## Test

```bash
python -m unittest discover tests
```

Tests cover the duplicate scanner and MD5 registry; the dialog test needs PyQt6
and is skipped without it.

## Build

`build.bat` builds a Windows one-dir PyInstaller app in `dist\MasterDownloader\`.
It bundles the local config, history, Instagram credentials and sessions into
the build, so build from a clean machine state if the output will be shared.

## Security note

The repository tracks `secret.key`, the Fernet key that encrypts the local
Instagram credentials and cookie files. Treat any credentials encrypted with it
as exposed to anyone with repository access.

## Where to go next

| Task | Page |
|---|---|
| Understand GUI/core split, threading, state files, encryption, packaging | [Architecture Overview](architecture/overview.md) |
| Fix or extend a TikTok, Instagram or Facebook download; cookies; archives; rate limits | [Platform Download Pipelines](workflows/platform-downloads.md) |
| Duplicate scanning, the deleted-MD5 registry, the delete dialog, and its tests | [Duplicate Cleanup and MD5 Registry](workflows/duplicate-cleanup.md) |
