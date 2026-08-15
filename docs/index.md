# Acervus

Acervus organizes files without moving them. You name the directories it should
watch, it records what it finds in a small database of its own, and you label
that record. Nothing on disk is renamed, moved, or written to. Delete the
database and your files are exactly as they were.

Two ways of organizing come with the tool:

- a **mark** is a label. A file can carry as many as you like, and a mark can be
  on as many files as you like.
- a **stack** is a named group. A file sits in at most one, so putting a file in
  a stack takes it out of the one it was in.

Marks answer *what is this file about*, and a file is usually about several
things at once. Stacks answer *what does this file belong with*, and a file
belongs with one set of things at a time. Between them they cover what folders
do, without a file having to be in only one place.

## How it works

```text
your directories            the index                 the interface
────────────────            ─────────                 ─────────────
~/docs        ──scan──▶  roots, files      ──▶  browse, filter,
~/photos                 marks, stacks          mark and stack
                         (one SQLite file)
```

You list your directories in a config file, under short names. Acervus reads
that file at startup and brings the index into line with it. A **scan** then
walks one of those directories and records the files it finds: their path
relative to the directory, their size, and when they last changed. From there
you browse the index and put marks and stacks on what you find.

Acervus reads your files' names and sizes. It never reads their contents, and
never writes to them.

## Where to go next

- [Getting started](getting-started.md) — install it, configure a directory,
  run the first scan.
- [Vocabulary](vocabulary.md) — every term the interface uses, defined once.
- [Configuration](configuration.md) — the config file, field by field.
- [Roots and scanning](roots-and-scanning.md) — what a scan changes, and what it
  leaves alone.
- [Marks and stacks](marks-and-stacks.md) — naming rules, and when they are
  created and deleted.
- [The interface](interface.md) — every screen and every key.
- [Troubleshooting](troubleshooting.md) — the messages you may see, and what
  they mean.

## Naming

**Acervus** is the project. **acre** is the command you type. A **mark** is a
label, a **stack** is a group of files. The name is Latin for a heap.
