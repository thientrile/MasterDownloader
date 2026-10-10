---
type: workflow
title: Platform Download Pipelines
description: How TikTok, Instagram and Facebook URLs are routed to yt-dlp or gallery-dl, which cookie sources are tried, where files and download archives land, and how rate limiting and failures are handled.
tags: [download, tiktok, instagram, facebook, yt-dlp, gallery-dl, cookies, rate-limit]
verified:
  - by: openwiki/0.6.0
    at: 2026-10-10T01:35:26.371Z
sources:
  - id: openwiki-source-54a3bad6602444acece2ba95
    resource: repo://App.py
  - id: openwiki-source-a79b6a13ff60f59805b684fc
    resource: repo://MasterDownloader.py
generated: { by: "claude-code", at: "2026-10-10T01:35:26.371Z" }
---

# Platform Download Pipelines

Each platform has one entry method on `MasterDownloader`:
`download_tiktok`, `download_instagram`, `download_facebook`. All accept
`(url, output_folder=None, progress_callback=None)`; the GUI passes the row's
folder and a callback (see [Architecture Overview](../architecture/overview.md)).

## Routing

- The GUI's `identify_platform` classifies by host: `tiktok.com`/`douyin.com`
  as TikTok, `instagram.com` as Instagram, `facebook.com`/`fb.watch` as
  Facebook; anything else is logged as unsupported.
- The console loop routes by substring and requires an Instagram session
  (`get_ig_session`) first.

## Target folder

- When the caller passes `output_folder`, it is used as is.
- The GUI resolves a folder before calling: an existing `saved_links` entry for
  the same platform and username wins, otherwise `<default_download_folder>/<username>`.
- Without a folder, the core calls `resolve_folder`, which looks up
  `history.json` by username (falling back to the legacy `platform:username`
  key), defaults to `<base_dir>/<username>`, rewrites old `TikTok_`/`IG_` folder
  names, and saves the mapping back.

## Download archives (no re-download)

yt-dlp downloads use a per-folder archive
`.masterdownloader_<platform>_ydl_<user>.txt`. Before the first use, any legacy
`archives/<platform>_<user>.txt` is merged into it line by line without
duplicates. `_prepare_yt_dlp` makes archive failures non-fatal: if the file
cannot be opened, or yt-dlp raises `EINVAL` on it, the archive is reset once and
otherwise disabled for that run.

Instagram uses a gallery-dl SQLite archive
`.masterdownloader_instagram_gallerydl_<target>.sqlite3` in the target folder.

Archives match by URL/post id only; content-level duplicates are handled by
[Duplicate Cleanup and MD5 Registry](duplicate-cleanup.md).

## yt-dlp common options

`_prepare_yt_dlp` layers shared rate-limit options (10 retries, 10-30 s sleep
between downloads, 5 s between requests, a browser user agent) under the
caller's options and points `ffmpeg_location` at `ffmpeg` on `PATH` or the
`imageio-ffmpeg` binary. Video format is `bestvideo*+bestaudio/best`, so
ffmpeg is needed to merge streams. Progress hooks forward percent, speed, ETA
and filename to `progress_callback`.

## TikTok

- `/story/` URLs go to `download_tiktok_story`, which maps story links to
  `/video/<id>` candidates because yt-dlp has no story extractor.
- Cookie strategies are tried in order: manual cookie from Settings (written
  to a temporary Netscape cookie file), Edge browser cookies, no cookies.
- A strategy is skipped on cookie-load errors or HTTP 429; any other error is
  raised to the worker, which marks the row as failed.
- Files are named `<upload_date> - <title> [<id>] - <playlist_index>.<ext>` and
  thumbnails are converted to JPG.

## Instagram

- `download_instagram` delegates entirely to `download_instagram_gallerydl`.
  The Instaloader-based code after that `return` is unreachable.
- gallery-dl runs as a subprocess (`python -m gallery_dl --config-ignore`) with
  sleeps of 20-45 s per item, 8-20 s per request and 300-900 s after a 429, and
  `extractor.instagram.include` chosen from the URL kind (profile, post, story,
  highlight). Profiles are capped at `ig_max_posts` (20).
- The manual Instagram cookie, when set, is passed as a temporary cookie file;
  without it gallery-dl still runs but private profiles and stories may fail.
- Exit code 0 means success. Otherwise the last output line decides the status:
  `429` starts a 6-hour Instagram cooldown, login/cookie/private/forbidden
  reports "Need Cookie", anything else reports the exit code. These failures are
  reported through `progress_callback`, not raised.

## Facebook

- Only `/videos/`, `/watch`, `/reel/` and `fb.watch/` links are accepted;
  other links are rejected with a console message.
- Strategies: Edge browser cookies, then no cookies. Unlike TikTok, every error
  moves on to the next strategy, and the last error is raised only after all
  strategies fail.

## Related

- [Architecture Overview](../architecture/overview.md)
- [Duplicate Cleanup and MD5 Registry](duplicate-cleanup.md)
