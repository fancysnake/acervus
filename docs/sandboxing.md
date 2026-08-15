# Running it sandboxed

Acervus writes to one file: the SQLite index at your `db_path`. Everything it
finds under a root it only reads — names, sizes, modification times — and
nothing under a root is ever renamed, moved, or written to.

That is a promise about how the code is written. If you would rather it were a
promise the operating system enforces, run `acre` under
[fence](#what-fence-is), with the profile the repository ships:

```bash
mkdir -p ~/.local/share/acervus
fence --settings fence.acervus.jsonc -- mise exec -- poetry run acre
```

Now a bug in a scan cannot touch an indexed file even if it tries: the kernel
refuses the write.

## What the profile allows

`fence.acervus.jsonc` sits in the repository root and says this much:

| | |
|---|---|
| **Reads** | anywhere — the point is to walk roots wherever they live |
| **Except** | `~/.ssh/id_*`, `~/.ssh/*.pem`, `~/.gnupg/`, `~/.aws/`, `~/.config/gcloud/`, `~/.netrc`, `~/.git-credentials`, `~/.pypirc` |
| **Writes** | `~/.local/share/acervus` and `/tmp` — nothing else |
| **Network** | none: no domains, no listening sockets, no outbound connections |
| **Terminal** | a PTY is allowed, because the interface is a terminal application |

Everything not named under `allowWrite` is read-only, which includes every root
you index. `/tmp` is there because SQLite spills temporary files for sorts and
large statements; it is not somewhere Acervus writes by choice.

The credential globs are a denied *read*. An indexer has no business opening a
private key, and refusing to is cheaper than trusting it not to.

## Before the first run

Create the database directory yourself:

```bash
mkdir -p ~/.local/share/acervus
```

fence skips a rule whose path does not exist, and Acervus creates the parent of
`db_path` on first use — so without the directory in place, the rule that would
have allowed the write is not there and the `mkdir` is denied.

## Adjusting it

!!! warning "The profile hardcodes the default `db_path`"
    `allowWrite` names `~/.local/share/acervus`. Point
    [`db_path`](configuration.md#db_path) somewhere else and the profile has to
    follow, or Acervus cannot open its own index.

Two other cases:

- **A root that contains credentials.** If you deliberately index a directory
  matched by one of the `denyRead` globs, drop that entry — otherwise those
  files are invisible to the scan.
- **A root on removable media.** No change needed. Reads are open everywhere,
  so a mounted drive is walked like any other directory.

## Why it is not called `fence.jsonc`

fence discovers a `fence.jsonc` by searching the working directory and its
parents. A file of that name in the repository root would therefore govern
*every* fence run started from the repository — including ones that have
nothing to do with Acervus, and that would be broken by a profile allowing no
network at all. The profile is named for what it sandboxes and passed
explicitly with `--settings`.

## What fence is

fence is a container-free sandbox that runs a command under kernel-level
network and filesystem restrictions. It is a development convenience here, not
a dependency: Acervus runs the same with or without it, and nothing in the code
knows it is there.

Running unsandboxed is the normal case, and the guarantee is the same one the
code makes on its own. The profile is for when you want the guarantee checked
by something other than the code.
