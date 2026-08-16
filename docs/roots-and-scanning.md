# Roots and scanning

## Roots come from the config

The interface lists roots but does not manage them. To add, remove, or move one,
edit `[acervus.roots]` in [the config](configuration.md#acervusroots) and restart
`acre`.

At startup Acervus reconciles the index against that table:

| In the config | In the index | What happens |
|---------------|--------------|--------------|
| yes | no | the root is added, with no files until you scan it |
| yes, same path | yes | nothing |
| yes, different path | yes | the path is updated, the indexed files are kept |
| no | yes | **the root is deleted, and its indexed files with it** |

The last row is the one to be careful with. Deleting a root takes its files out
of the index, and their marks and stack membership go with them. Nothing on disk
changes, but the organizing you did of those files is gone. An alias you rename
in the config reads as one root deleted and another added, with the same effect.

## What a scan does

Press ++s++ on the roots screen with the cursor on a root. Acervus walks that
directory and compares what it finds against what the index holds for that
root:

- a file the directory has and the index lacks is **added**
- a file whose size or modification time has moved is **updated**
- a file the index holds and the directory no longer has is **removed**
- a file the two agree on is left alone

The result is reported under the table:

```text
docs: 12 added, 3 removed, 1 updated.
```

A rescan of a directory nothing has touched writes nothing and reports three
zeros.

Only regular files are recorded. Directories are walked through, not indexed.
A path that cannot be read — a broken symlink, a directory without permission,
a file that disappears mid-walk — is passed over rather than aborting the scan,
because a live directory tree changes while it is being read.

## What a scan preserves

The index tracks a file by its root and its relative path, and marks and stack
membership hang off that record. So:

- editing a file keeps its marks; only its recorded size and time change
- deleting a file removes it from the index at the next scan, with its marks
- **moving or renaming a file loses its marks.** The old path is gone and the
  new one is a file Acervus has not seen before. There is no rename detection.

Scan one root at a time, whichever ones you have changed. Acervus never scans on
its own, and does not watch the filesystem for changes.

## When a root is not there

An unmounted drive or a deleted directory reads as empty, and scanning it would
mean deleting every file indexed under it. Acervus refuses instead:

```text
Root 'photos' is not at /mnt/media/photos, so nothing was scanned.
```

Nothing is written. Mount the drive, or fix the path in the config, and scan
again.

## Scanning a large tree

A scan runs off the interface thread, so the display keeps redrawing and the
keys keep working while a big directory is walked. The status line shows
`Scanning docs…` until the count arrives.
