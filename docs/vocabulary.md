# Vocabulary

Every word the interface uses, in one place. The terms are deliberately few.

## Root

A directory you have told Acervus to watch, under a short name of your choosing.
The name is the **alias**, the directory is the **path**:

```toml
[acervus.roots]
docs = "/home/user/docs"
```

Here `docs` is the alias and `/home/user/docs` is the path. Aliases are how you
refer to a root everywhere else — the roots screen lists them, the files screen
browses one of them at a time, a scan reports under them.

Roots come only from the config file. You cannot add or remove one from the
interface, and Acervus reconciles the index against the config every time it
starts. See [Roots and scanning](roots-and-scanning.md).

## File

A file Acervus found under a root. It is recorded by the root it belongs to and
its path **relative to that root**, so `~/docs/tax/2025.pdf` under the `docs`
root is stored as `tax/2025.pdf`. Its size and modification time are recorded
too, which is how a scan tells a changed file from an untouched one.

Only regular files are indexed. Directories are walked, not recorded, and
symlinks that lead nowhere are passed over.

Files are never created, deleted, moved, or edited by Acervus. Deleting a file
*from the index* — which a scan does when the file is gone from disk — has no
effect on the disk.

## Index

The record Acervus keeps: the roots, the files under them, the marks, the stacks,
and which file carries or sits in what. It is one SQLite file, at the `db_path`
your config names. It is the only thing Acervus writes.

The index is a description of your disk, not a copy of it. It goes stale as soon
as you change something outside Acervus, and a [scan](roots-and-scanning.md) is
what brings it up to date.

## Scan

Walking one root and bringing the index into line with what is there now. Files
the root has and the index lacks are added, files whose size or modification
time has moved are rewritten, files the index holds and the root no longer has
are dropped. Everything else is left untouched.

A scan is something you ask for, on the roots screen, one root at a time.
Acervus does not scan on its own or watch for changes in the background.

## Mark

A label on a file. Many-to-many in both directions: one file can carry `invoice`,
`2025` and `scanned` at once, and `invoice` can be on a thousand files.

A mark comes into being the first time you put it on a file, and is deleted once
the last file stops carrying it. There is no separate step for creating or
retiring one. Names may not contain spaces. See
[Marks and stacks](marks-and-stacks.md).

## Stack

A named group of files. A file sits in **at most one stack**, so putting a file
in a stack takes it out of whichever one it was in. A stack that this leaves
empty is deleted.

Like a mark, a stack is created by being used. Unlike a mark, a stack name may
contain spaces — it is never packed into a list beside other names, so nothing
has to split it apart again.

## Bare, unmarked, unstacked

A file carrying no mark at all is **unmarked**; a file sitting in no stack is
**unstacked**. Both are filters on the files screen: the mark filter and the
stack filter each end their cycle on the bare case, so you can browse exactly
the part of a root you have not organized yet.

## Alias

The short name a root goes by. Unique across the index, and yours to choose.

## Ignore pattern

A glob the scanner refuses to walk into or record. Patterns are matched against
one path component at a time, so `.venv` skips a directory of that name at any
depth and `*.pyc` skips a file anywhere. See
[Configuration](configuration.md#ignore).
