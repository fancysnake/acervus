# Troubleshooting

## `acre` exits immediately

```text
No config found. Create ~/.config/acervus/config.toml (see config.example.toml).
```

There is no config file at that path. Acervus does not run without one; see
[Configuration](configuration.md).

```text
The config is there but not usable:
...
```

The file exists but does not parse or does not validate. The lines that follow
name the field at fault — a missing `[acervus]` table, a `db_path` that is not a
string, a root path of the wrong type.

## `No roots configured.`

The `[acervus.roots]` table is empty or absent. Add `alias = "path"` entries and
restart.

## A scan reports nothing was scanned

```text
Root 'photos' is not at /mnt/media/photos, so nothing was scanned.
```

The directory is not there — unmounted, renamed, or the path in the config is
wrong. Acervus refuses rather than reading it as empty and deleting every file
indexed under it. Nothing was written.

## A scan finds fewer files than expected

Check your [`ignore` patterns](configuration.md#ignore). Writing the key replaces
the default list, and each pattern matches a single path component, so
`node_modules/*` matches nothing while `node_modules` prunes the directory.

Only regular files are indexed: directories, sockets, and symlinks that lead
nowhere are not. Files in directories Acervus cannot read are skipped silently.

## My marks are gone

Three ways that happens, all of them recoverable only by marking again:

- **A file was moved or renamed.** Acervus tracks a file by its path relative to
  its root; a moved file is a new file at the next scan, and the old record is
  dropped with its marks.
- **A root left the config.** Removing or renaming an alias in
  `[acervus.roots]` deletes that root from the index at the next start, along
  with every file under it.
- **The index file was deleted or `db_path` changed.** Marks live in the index,
  nowhere else.

## A mark shows a count of zero

Its files were dropped — by a scan, or with a root that left the config — rather
than unmarked. A mark is deleted when the last file is taken *off* it, which
never happened here. Put that mark on any file and take it off again to clear
it.

## The files screen is empty

`No files indexed. Scan a root first.` means the index has no files at all: go to
the roots screen and press ++s++.

`No files match this filter.` means the filters are too narrow. Step each of
++r++, ++k++ and ++c++ back around to *all roots*, *any mark* and *any stack* —
the line above the table shows where each one stands.

## A name is rejected

```text
A mark name cannot contain whitespace: 'tax return'.
```

Mark names take no whitespace, no `:` and no `,`, and cap at 64 characters.
Stack names allow spaces and cap at 255. Both must be non-empty. See
[Marks and stacks](marks-and-stacks.md#names).

## The interface freezes during a scan

It should not — a scan runs off the interface thread. If a very large root makes
the display sluggish, the scan is competing for the disk rather than blocking
the interface; the count arrives when the walk finishes.

## Starting over

The index is one file, at your `db_path`. Delete it and Acervus rebuilds an
empty one on the next start; scan your roots to refill it. Your files on disk
are never touched by this, but every mark and stack is lost.
