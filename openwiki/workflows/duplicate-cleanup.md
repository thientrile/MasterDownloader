---
type: workflow
title: Duplicate Cleanup and MD5 Registry
description: How MasterDownloader finds content-identical images and videos, lets the user confirm deletions, and remembers deleted files by MD5 so re-downloaded copies are flagged on the next scan.
tags: [dedup, md5, workflow, gui, testing]
verified:
  - by: openwiki/0.6.0
    at: 2026-10-10T01:35:26.371Z
sources:
  - id: openwiki-source-54a3bad6602444acece2ba95
    resource: repo://App.py
  - id: openwiki-source-a7f30af9ee540fb794ce7065
    resource: repo://docs/superpowers/specs/2026-06-19-md5-deleted-dedup-design.md
  - id: openwiki-source-a79b6a13ff60f59805b684fc
    resource: repo://MasterDownloader.py
  - id: openwiki-source-325376993cc5382017cdb9f7
    resource: repo://tests/test_dedup_dialog.py
  - id: openwiki-source-6c548cfebdee31c60af068cf
    resource: repo://tests/test_dedup_md5.py
generated: { by: "claude-code", at: "2026-10-10T01:35:26.371Z" }
---

# Duplicate Cleanup and MD5 Registry

Download archives only stop re-downloading the same URL or post id. The same
content can still arrive through a different URL (a repost, a story vs. a post,
TikTok vs. Instagram). The duplicate cleanup finds those files by content and
remembers what was deleted.

## User flow

1. The user clicks the scan button; `scan_duplicates_ui` asks for a folder
   (starting at the default download folder) and runs a `DuplicateWorker` on the
   thread pool. The button stays disabled until the worker finishes.
2. The worker calls `MasterDownloader.find_duplicates`, which returns
   `(groups, resurrected)`.
3. `DuplicatesDialog` lists each group with its first (oldest) file marked as
   kept and not checkable; every other copy and every resurrected file starts
   checked for deletion.
4. On confirm, `delete_paths` deletes the checked paths and the GUI reports the
   count and bytes freed.

## Scan algorithm (`find_duplicates`)

- Walks the directory, skipping paths containing `sessions`, `__pycache__`,
  `.git` or `archives`, and considers only image/video extensions with non-zero
  size.
- Groups candidates by size, then by a BLAKE2b signature of the first 64 KB, and
  only then by full-file MD5. A full hash is computed only for files that share
  both size and head signature.
- Each duplicate group is sorted by `(mtime, path)`, so element 0 is the oldest
  file, the one to keep.
- **Resurrected files**: any file whose size appears in the deleted-MD5
  registry has its MD5 computed; a match means previously deleted content came
  back. A resurrected file that is also inside a duplicate group is reported
  only in the group.

## Deleted-MD5 registry

- Single global file `archives/deleted_md5.txt`, one `md5,size` line per entry,
  shared across platforms and users.
- Loaded at startup into `size -> set(md5)`; malformed lines are skipped.
- `delete_paths` hashes each file *before* removing it and calls
  `_record_deleted_md5`, which is idempotent (in memory and on disk).
- The registry is only written during dedup deletion; downloads do not consult
  it. A resurrected file is cleaned up on the next scan, not blocked at download
  time. This is the decision recorded in
  `docs/superpowers/specs/2026-06-19-md5-deleted-dedup-design.md`.

## Tests

Run with `python -m unittest discover tests`.

- `tests/test_dedup_md5.py` builds a `MasterDownloader` via `object.__new__`
  (skipping the heavy constructor) and covers MD5 hashing, registry round-trip,
  idempotence, malformed lines, delete-then-record, resurrected detection,
  same-size-different-content, and de-duplication between groups and
  resurrected files.
- `tests/test_dedup_dialog.py` checks that resurrected files are selectable in
  `DuplicatesDialog` and the keeper is not; it uses the offscreen Qt platform
  and is skipped when PyQt6 cannot be imported.

## Related

- [Platform Download Pipelines](platform-downloads.md)
- [Architecture Overview](../architecture/overview.md)
