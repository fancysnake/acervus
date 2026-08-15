# The interface

`acre` opens a terminal interface with four screens. Arrow keys move the cursor
in any table; the footer always shows the keys the current screen accepts.

## Keys that work anywhere

| Key | Does |
|-----|------|
| ++f++ | open the files screen |
| ++m++ | open the marks screen |
| ++t++ | open the stacks screen |
| ++q++ | quit |

++escape++ goes back from the files, marks and stacks screens to the one
underneath. The roots screen is the bottom of the stack, so ++escape++ does
nothing there — leave with ++q++.

While a name prompt is open your keystrokes go into the text field, so the keys
above do not fire until you submit with ++enter++ or back out with ++escape++.

## Roots

The screen Acervus opens on. Lists every root in the index, alias and path, in
alphabetical order by alias.

| Key | Does |
|-----|------|
| ++s++ | scan the root under the cursor |

The line under the table reports the scan: `Scanning docs…` while it runs, then
`docs: 12 added, 3 removed, 1 updated.` when it finishes. See
[Roots and scanning](roots-and-scanning.md).

Roots are added and removed by editing the config, not here. `No roots
configured.` means the `[acervus.roots]` table is empty.

## Files

Every indexed file, as `Root`, `Path` and `Size` in bytes, narrowed by whatever
filters are on. `Path` is relative to the root.

Under the table are three lines: the marks the file under the cursor carries,
the stack it sits in, and the result of whatever you last did. They follow the
cursor as it moves.

| Key | Does |
|-----|------|
| ++r++ | step the root filter |
| ++k++ | step the mark filter |
| ++c++ | step the stack filter |
| ++a++ | put a mark on the file under the cursor |
| ++x++ | take a mark off the file under the cursor |
| ++s++ | put the file under the cursor in a stack |
| ++u++ | take the file under the cursor out of its stack |

The filter keys take a consonant from the noun, since ++m++ and ++s++ are
spoken for: mar<strong>k</strong>, sta<strong>c</strong>k.

Marking is covered in [Marks and stacks](marks-and-stacks.md).

### Filtering

Each of the three keys steps its filter one stop forward and wraps around. The
line above the table always says where you are:

```text
Showing: docs, invoice, unstacked
```

- ++r++ cycles *all roots*, then each root in turn. There is no bare stop —
  every file has a root.
- ++k++ cycles *any mark*, then each mark in turn, then *unmarked*.
- ++c++ cycles *any stack*, then each stack in turn, then *unstacked*.

The three narrow together, so `docs, invoice, unstacked` lists the files under
`docs` that carry `invoice` and sit in no stack. `unmarked` and `unstacked` are
how you find what you have not organized yet.

Each key re-reads the list it cycles when you press it, so a mark you created a
moment ago is already in the cycle. A filter you were on when its mark or stack
was deleted drops you back to the unfiltered stop rather than failing.

An empty table says `No files indexed. Scan a root first.` when nothing is
indexed at all, and `No files match this filter.` when the filters are simply
too narrow.

## Marks

Every mark in use, with how many files carry it, ordered by name. A read-only
list: marks are made and unmade from the files screen, and a mark nothing
carries is already gone. `No marks yet. Put one on a file from the files
screen.` when there are none.

## Stacks

Every stack, with how many files sit in it, ordered by name. Move the cursor and
the lines below show what is inside the stack under it, one relative path per
line. Read-only, like the marks screen.
