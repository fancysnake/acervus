# Configuration

Acervus reads one TOML file at `~/.config/acervus/config.toml`. There is no
command-line option and no environment variable; if the file is not there,
`acre` says so and exits.

Everything lives under an `[acervus]` table:

```toml
[acervus]
db_path = "~/.local/share/acervus/acervus.db"
ignore = [".git", ".venv", "node_modules", "__pycache__"]

[acervus.roots]
docs = "~/docs"
photos = "/mnt/media/photos"
```

## `db_path`

**Required.** The SQLite file the index lives in. A leading `~` expands to your
home directory. The file and any missing parent directories are created the
first time Acervus needs them.

Point two configs at the same path and they share one index; point them at
different paths and you have two independent ones. Deleting the file discards
every mark and stack you have made — and nothing else.

## `[acervus.roots]`

**Required.** The directories Acervus watches, as `alias = "path"`. The alias is
a short name of your choosing, unique across the table; the path is the
directory, with `~` expanded as above.

```toml
[acervus.roots]
docs = "~/docs"
photos = "/mnt/media/photos"
```

The table may be empty, in which case there is nothing to scan.

!!! warning "Removing a root removes its files from the index"
    Acervus reconciles the index against this table on every start. An alias you
    delete here is deleted from the index too, and its indexed files go with it,
    taking their marks and stack membership. Your files on disk are untouched,
    but the labelling of them is gone. Renaming an alias counts as deleting one
    and adding another.

    Changing only the *path* under an existing alias keeps the files indexed;
    the next scan reconciles them against the new directory.

## `ignore`

**Optional.** Glob patterns a scan will not walk into or record. The default is:

```toml
ignore = [".git", ".venv", "node_modules", "__pycache__"]
```

Each pattern is matched against **one path component at a time**, not against
the whole path. So `.venv` skips a directory of that name at any depth, `*.pyc`
skips a file anywhere, and `node_modules/*` matches nothing at all, because no
single component ever contains a slash.

A matching directory is pruned rather than filtered, so skipping a large
`node_modules` costs nothing to walk.

Writing the key **replaces** the default list rather than adding to it. To keep
the defaults and add your own, write them out in full:

```toml
ignore = [".git", ".venv", "node_modules", "__pycache__", "*.tmp", ".cache"]
```

To index everything, including the defaults:

```toml
ignore = []
```

Changing `ignore` affects the next scan, not the index as it stands. Files
already indexed that a new pattern would now skip are dropped the next time you
scan the root holding them.

## When the config is wrong

A file that is missing and a file that is malformed are reported the same way:
a message on standard error and exit status 1. A malformed file names the field
at fault, for instance a `db_path` that is not a string, or `[acervus.roots]`
missing altogether.
