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

One directory of one root at a time. The screen opens at the top of the first
root and you walk down into it, the way a file manager works.

The rows come in the order the directory reads: `..` where there is somewhere
to go back to, then the subdirectories, then the files sitting in this
directory itself. `Name` is the directory or file, `Files` counts everything
underneath a directory, and `Size` is the file's own size in bytes. The
unheaded first column holds a `•` on each selected file.

Under the table are three lines: the marks the file under the cursor carries,
the stack it sits in, and the result of whatever you last did. They follow the
cursor as it moves, and say nothing on a directory row.

| Key | Does |
|-----|------|
| ++enter++ | open the directory under the cursor, or go back up from `..` |
| ++backspace++ | go up to the directory holding this one |
| ++r++ | move to the next root, at the top of it |
| ++k++ | step the mark filter |
| ++c++ | step the stack filter |
| ++space++ | select the file under the cursor, or deselect it |
| ++a++ | put a mark on every file selected |
| ++x++ | take a mark off every file selected |
| ++s++ | put every file selected in a stack |
| ++u++ | take every file selected out of its stack |

The filter keys take a consonant from the noun, since ++m++ and ++s++ are
spoken for: mar<strong>k</strong>, sta<strong>c</strong>k.

Marking is covered in [Marks and stacks](marks-and-stacks.md).

### Browsing

++enter++ opens the directory under the cursor; ++backspace++ goes back up, and
leaves the cursor on the directory you came out of, so walking a tree and
walking back out of it cost the same. The line above the table says where you
are:

```text
Showing: docs > photos/2024, any mark, any stack
```

At the top of a root there is nowhere further up, so there is no `..` row and
++backspace++ does nothing; ++r++ moves to the next root. ++escape++ leaves the
screen altogether rather than going up a level.

Directories are not rows in the index — Acervus indexes files, and a directory
is what their paths have in common. So a directory holding no indexed file does
not appear, and no key here acts on a directory: ++a++, ++x++, ++s++, ++u++ and
++space++ do nothing at all with the cursor on one. Marking a whole tree in one
keypress is deliberately not offered.

### Selecting

++space++ selects the file under the cursor, putting a `•` in front of it, and
++space++ again deselects it. The status line says how many are selected.

The four operations are aimed at the selection. With nothing selected they are
aimed at the file under the cursor instead, so a screen you never press
++space++ on behaves exactly as before.

A selection is a set of files, not of rows, so it survives the cursor moving
away and the rows being redrawn. Moving anywhere else clears it — opening a
directory, going up, stepping a filter or moving to another root. The rows you
land on are not the rows that were selected.

### Long directories

A directory's files are read a page at a time. One holding hundreds of
thousands would otherwise have to be read out in full before a single row could
be drawn, which is a wait long enough to look like a hang; instead the first
page is drawn at once and the next is read as the cursor comes near the end of
what is on screen. Moving down, you will not notice; ++ctrl+end++ jumps to the
end of what has been read so far, so in a very long directory it takes more
than one press to reach the true end.

### Filtering

++k++ and ++c++ each step one stop forward and wrap around, narrowing what the
directory you are in shows:

- ++k++ cycles *any mark*, then each mark in turn, then *unmarked*.
- ++c++ cycles *any stack*, then each stack in turn, then *unstacked*.

They narrow together, and they narrow the directory rows too: `Files` counts
only what matches, and a directory holding nothing that matches is not listed
at all. So `unmarked` turns the browser into a walk through exactly the part of
the tree you have not organized yet.

Each key re-reads the list it cycles when you press it, so a mark you created a
moment ago is already in the cycle. A filter you were on when its mark or stack
was deleted drops you back to the unfiltered stop rather than failing.

An empty table says `No roots configured.` when the config names none, `No
files indexed. Scan a root first.` when this directory holds nothing, and `No
files match this filter.` when the filters are simply too narrow.

## Marks

Every mark in use, with how many files carry it, ordered by name. A read-only
list: marks are made and unmade from the files screen, and a mark nothing
carries is already gone. `No marks yet. Put one on a file from the files
screen.` when there are none.

## Stacks

Every stack, with how many files sit in it, ordered by name. Move the cursor and
the lines below show what is inside the stack under it, one relative path per
line. Read-only, like the marks screen.
