# Getting started

## Requirements

- Python 3.14
- [Poetry](https://python-poetry.org/) for dependencies
- [mise](https://mise.jdx.dev/) for the toolchain

## Install

```bash
mise install
poetry install
```

That gives you the `acre` command.

## Write a config

Acervus does not run without one. It reads
`~/.config/acervus/config.toml`, and there is a
[`config.example.toml`](https://github.com/fancysnake/acervus/blob/main/config.example.toml)
in the repository to copy:

```toml
[acervus]
db_path = "~/.local/share/acervus/acervus.db"

[acervus.roots]
docs = "~/docs"
photos = "~/photos"
```

`db_path` is where the index will live; its directory is created for you if it
is not there. Under `[acervus.roots]` you name the directories to watch, one
`alias = "path"` per line. A leading `~` means your home directory in both.

Every field is explained in [Configuration](configuration.md).

## Run it

```bash
acre
```

Acervus reads the config, brings the index into line with the roots it names,
and opens on the roots screen:

```text
 Acervus
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Alias   ┃ Path                ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ docs    │ /home/user/docs     │
│ photos  │ /home/user/photos   │
└─────────┴─────────────────────┘

 s Scan   f Files   m Marks   t Stacks   q Quit
```

## Your first scan

The index knows your roots but nothing under them yet. Put the cursor on a root
with the arrow keys and press ++s++. Acervus walks the directory and reports
what changed:

```text
docs: 1284 added, 0 removed, 0 updated.
```

Large trees take a while; the interface stays responsive while the scan runs.
Scan the other roots the same way.

## Mark something

Press ++f++ for the files screen. It lists every indexed file, with the root it
came from, its path within that root, and its size. Under the table, two lines
show what the file under the cursor carries and which stack it sits in.

Move to a file and press ++a++. A prompt asks for a mark name; type `invoice`
and press ++enter++. The status line confirms it, and the marks line for that
file now reads `Marks: invoice`. The mark did not exist a moment ago — putting
it on a file is what created it.

Press ++x++ to take a mark off again, naming it the same way. Press ++s++ to
put the file in a stack, and ++u++ to take it back out.

## Find it again

Still on the files screen, press ++k++ to step the mark filter forward. It
cycles through *any mark*, then each mark in turn, then *unmarked*, and back
around. The line above the table always says what you are looking at:

```text
Showing: all roots, invoice, any stack
```

++r++ does the same for roots and ++c++ for stacks, and the three filters
combine — root `docs`, mark `invoice`, unstacked, if that is what you need.

## Where next

- [The interface](interface.md) for every screen and key.
- [Marks and stacks](marks-and-stacks.md) for the naming rules and what happens
  to a mark nothing carries.
- [Roots and scanning](roots-and-scanning.md) before you change a root in the
  config — dropping one drops its files from the index.
