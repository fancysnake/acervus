# Manual Test Scenarios

Based on: `mvp` vs `main`
Changes in: Startup & configuration, Roots screen & scanning, Files screen
(browsing, filtering, marking, stacking), Marks screen, Stacks screen, Name
prompt, Navigation, Data integrity & persistence

The branch introduces the whole MVP, so the scope is the entire application:
config loading, the SQLite index, the filesystem scan, and all five Textual
screens.

---

## Test data setup

Prepare this once; most scenarios reuse it.

```
/tmp/qa/docs/
  report.txt              (some content)
  notes.md
  sub/deep/manual.pdf
  "spaced name.txt"
  ünïcode.txt
  .hidden.txt
  empty.txt               (0 bytes)
  emptydir/               (directory, no files)
  link-ok  -> report.txt  (symlink to an existing file)
  link-dead -> nowhere    (broken symlink)
/tmp/qa/photos/
  a.jpg
  b.jpg
```

Config at `~/.config/acervus/config.toml`:

```toml
[acervus]
db_path = "~/.local/share/acervus/qa.db"

[acervus.roots]
docs   = "/tmp/qa/docs"
photos = "/tmp/qa/photos"
```

Run the app with `acre`. To start from a clean index, delete the db file
(`~/.local/share/acervus/qa.db` plus any `-wal` / `-shm` siblings).

---

## Startup & Configuration

### No config file at all

**Preconditions:** `~/.config/acervus/config.toml` does not exist (move it
aside).

- [ ] Run `acre` → Expected: no TUI opens; stderr prints `No config found.
      Create ~/.config/acervus/config.toml (see config.example.toml).`
- [ ] Run `echo $?` → Expected: `1`
- [ ] Confirm no database file was created at the configured `db_path` →
      Expected: the file is absent (a missing config never touches the disk)

### Malformed config — missing required key

**Preconditions:** config file exists but has no `db_path`:

```toml
[acervus]
[acervus.roots]
docs = "/tmp/qa/docs"
```

- [ ] Run `acre` → Expected: stderr prints `The config is there but not
      usable:` followed by a Pydantic validation error naming `db_path` as
      missing; no traceback
- [ ] Run `echo $?` → Expected: `1`

### Malformed config — broken TOML syntax

**Preconditions:** config file contains invalid TOML, e.g. `db_path = ` with no
value.

- [ ] Run `acre` → Expected: it fails loudly rather than opening the TUI
- [ ] Note the exact output → Expected: this path raises a `tomllib` decode
      error, *not* the friendly `BAD_CONFIG_MESSAGE`. **Flag if the raw
      traceback is unacceptable UX** — only `ValidationError` is caught in
      `wiring.main`

### Missing `[acervus]` table

**Preconditions:** config file contains only `db_path = "..."` at top level,
with no `[acervus]` table.

- [ ] Run `acre` → Expected: `The config is there but not usable:` plus a
      validation error naming the `acervus` field, exit code 1

### Config with no roots at all

**Preconditions:** valid config, `[acervus.roots]` present but empty.

- [ ] Run `acre` → Expected: the TUI opens on the roots screen showing
      `No roots configured.`; the roots table is not displayed
- [ ] Press `s` → Expected: nothing happens, no crash, no error text
- [ ] Press `f` → Expected: the files screen opens showing `No files indexed.
      Scan a root first.`
- [ ] Press `q` → Expected: the app exits cleanly

### Tilde expansion in paths

**Preconditions:** config uses `~` in both `db_path` and a root path, e.g.
`db_path = "~/.local/share/acervus/qa.db"` and `home = "~/"`.

- [ ] Run `acre` → Expected: the roots screen shows the root with its **fully
      expanded** absolute path (`/home/<user>/`), not a literal `~`
- [ ] Check the filesystem → Expected: the database file exists at the expanded
      `db_path`

### Database directory is created on first run

**Preconditions:** `db_path` points into a directory that does not exist, e.g.
`~/.local/share/acervus/brand/new/qa.db`.

- [ ] Run `acre` → Expected: the TUI opens; the missing parent directories are
      created
- [ ] Check the filesystem → Expected: `qa.db` exists at that path
- [ ] Quit with `q`, then check for leftover locks → Expected: the process
      exits; no stale `-wal` file blocks a second run

### Database file is unwritable

**Preconditions:** `db_path` points at a directory you have no write permission
for (e.g. `/qa.db`).

- [ ] Run `acre` → Expected: it fails with a permission error rather than
      hanging or silently opening an empty TUI. Record the exact message —
      **flag if it is a bare traceback**

---

## Roots Screen

### Roots screen lists the configured roots

**Preconditions:** the standard test config (docs + photos), fresh index.

- [ ] Run `acre` → Expected: the app opens on the roots screen, titled
      `Acervus`
- [ ] Read the table → Expected: two columns, `Alias` and `Path`; two rows,
      `docs` and `photos`
- [ ] Check the row order → Expected: ordered by alias, so `docs` comes before
      `photos`
- [ ] Check the footer → Expected: shows the bindings `Files`, `Marks`,
      `Stacks`, `Quit`, `Scan`
- [ ] Confirm `No roots configured.` is **not** visible

### Scanning a root for the first time

**Preconditions:** fresh index; cursor on the `docs` row.

- [ ] Press `s` → Expected: a status line appears, first `Scanning docs…`, then
      `docs: N added, 0 removed, 0 updated.`
- [ ] Count the expected `N` → Expected: it counts every **regular file**
      recursively — `report.txt`, `notes.md`, `sub/deep/manual.pdf`,
      `spaced name.txt`, `ünïcode.txt`, `.hidden.txt`, `empty.txt`, and
      `link-ok` (a symlink to a regular file resolves to one). It does **not**
      count `emptydir/`, `sub/`, `sub/deep/`, or `link-dead`
- [ ] Press `f` to open the files screen → Expected: every counted file is
      listed with its path relative to the root, not its absolute path

### Rescanning an unchanged root writes nothing

**Preconditions:** `docs` has just been scanned; nothing on disk has changed.

- [ ] Cursor on `docs`, press `s` → Expected: `docs: 0 added, 0 removed,
      0 updated.`
- [ ] Press `s` again → Expected: the same result, every time

### Scan picks up an added file

**Preconditions:** `docs` scanned; app still running on the roots screen.

- [ ] In another terminal, `touch /tmp/qa/docs/newfile.txt`
- [ ] Cursor on `docs`, press `s` → Expected: `docs: 1 added, 0 removed,
      0 updated.`
- [ ] Press `f` → Expected: `newfile.txt` appears in the listing
- [ ] Press `escape`, then `s` again → Expected: `0 added, 0 removed,
      0 updated.`

### Scan picks up a deleted file

**Preconditions:** `docs` scanned and contains `newfile.txt`.

- [ ] In another terminal, `rm /tmp/qa/docs/newfile.txt`
- [ ] Cursor on `docs`, press `s` → Expected: `docs: 0 added, 1 removed,
      0 updated.`
- [ ] Press `f` → Expected: `newfile.txt` is gone from the listing

### Scan picks up a changed file (size)

**Preconditions:** `docs` scanned.

- [ ] Note the `Size` column value for `report.txt` on the files screen, then
      return to roots with `escape`
- [ ] In another terminal, `echo "more text" >> /tmp/qa/docs/report.txt`
- [ ] Press `s` → Expected: `docs: 0 added, 0 removed, 1 updated.`
- [ ] Press `f` → Expected: `report.txt` shows the **new, larger** size

### Scan picks up a changed file (mtime only)

**Preconditions:** `docs` scanned.

- [ ] In another terminal, `touch /tmp/qa/docs/notes.md` (content and size
      unchanged)
- [ ] Press `s` → Expected: `docs: 0 added, 0 removed, 1 updated.` — an mtime
      move alone counts as an update
- [ ] Press `s` again → Expected: `0 added, 0 removed, 0 updated.`

### Scan reports added, removed and updated together

**Preconditions:** `docs` scanned.

- [ ] In another terminal, in one go: create `fresh.txt`, delete `notes.md`,
      append to `report.txt`
- [ ] Press `s` → Expected: `docs: 1 added, 1 removed, 1 updated.` — all three
      counters in one message
- [ ] Press `f` → Expected: `fresh.txt` present, `notes.md` absent,
      `report.txt` at its new size

### Scanning an unavailable root is refused, not destructive

**Preconditions:** `photos` scanned so its files are indexed and at least one
of them carries a mark and sits in a stack.

- [ ] In another terminal, `mv /tmp/qa/photos /tmp/qa/photos-away`
- [ ] Cursor on `photos`, press `s` → Expected: the status line reads
      `Root 'photos' is not at /tmp/qa/photos, so nothing was scanned.`
- [ ] Press `f` → Expected: the photos files are **still indexed**; the marks
      and stack they carried are intact
- [ ] Restore the directory (`mv /tmp/qa/photos-away /tmp/qa/photos`), press
      `s` → Expected: `photos: 0 added, 0 removed, 0 updated.` — the index was
      never damaged

### Scanning a root that is a file, not a directory

**Preconditions:** config names a root whose path is a regular file, e.g.
`odd = "/tmp/qa/docs/report.txt"`.

- [ ] Start `acre`, cursor on `odd`, press `s` → Expected: the
      `Root 'odd' is not at …, so nothing was scanned.` message; no files are
      indexed under it, no crash

### Scan on an empty roots table does nothing

**Preconditions:** config with no roots.

- [ ] Press `s` on the roots screen → Expected: no status text, no exception,
      the screen is unchanged

### The interface stays responsive during a long scan

**Preconditions:** a root pointing at a large tree (thousands of files, e.g.
`big = "/usr/share"`).

- [ ] Cursor on `big`, press `s` → Expected: `Scanning big…` appears
      **immediately**, before the scan finishes
- [ ] While it runs, press the arrow keys → Expected: the cursor still moves —
      the UI is not frozen
- [ ] While it runs, press `f` → Expected: the files screen opens without
      hanging (it may show a partial listing; the scan commits at the end)
- [ ] Return with `escape` and wait → Expected: the final
      `big: N added, 0 removed, 0 updated.` line replaces `Scanning big…`
- [ ] Press `f` again → Expected: the full file set is now listed

---

## Files Screen

### Empty index shows the right empty state

**Preconditions:** roots configured, nothing scanned yet.

- [ ] Press `f` → Expected: `No files indexed. Scan a root first.`
- [ ] Confirm the files table is not displayed
- [ ] Press `a` → Expected: no prompt opens (there is no file under the cursor)
- [ ] Press `x`, `s`, `u` → Expected: nothing happens, no crash

### Files listing shows root, path and size

**Preconditions:** both roots scanned.

- [ ] Press `f` → Expected: columns `Root`, `Path`, `Size`
- [ ] Read the `Root` column → Expected: it shows the **alias** (`docs`,
      `photos`), not a numeric id
- [ ] Read the `Path` column → Expected: paths relative to the root, with
      subdirectories shown as `sub/deep/manual.pdf`
- [ ] Check the ordering → Expected: grouped by root, then by relative path
      within each root
- [ ] Find `empty.txt` → Expected: `Size` is `0`
- [ ] Find `ünïcode.txt` and `spaced name.txt` → Expected: both render with
      their names intact, no mojibake or truncation
- [ ] Check the filter line at the top → Expected: `Showing: all roots, any
      mark, any stack`

### Moving the cursor updates the marks and stack lines

**Preconditions:** files indexed; one file carries marks, another carries none.

- [ ] Put the cursor on an unmarked, unstacked file → Expected: `Marks: none`
      and `Stack: none`
- [ ] Arrow down to a file carrying two marks → Expected: `Marks: <a>, <b>`
      with the names comma-separated and alphabetically ordered
- [ ] Arrow to a file in a stack → Expected: `Stack: <name>`
- [ ] Arrow back to the unmarked file → Expected: the lines reset to
      `Marks: none` / `Stack: none`

---

## Marking Files

### Add a mark to a file

**Preconditions:** files screen open, cursor on `report.txt`, no marks exist.

- [ ] Press `a` → Expected: a modal appears reading `Mark to add:` with an
      input focused
- [ ] Type `invoice` and press Enter → Expected: the modal closes; status reads
      `Marked report.txt invoice.`; the `Marks:` line reads `Marks: invoice`
- [ ] Press `m` → Expected: the marks screen lists `invoice` with `Files` = `1`
- [ ] Press `escape`, then `escape` → Expected: back on the roots screen

### Add a second mark to the same file

**Preconditions:** `report.txt` carries `invoice`.

- [ ] Cursor on `report.txt`, press `a`, type `2026`, Enter → Expected:
      `Marked report.txt 2026.`; the `Marks:` line reads `Marks: 2026, invoice`
      (alphabetical)
- [ ] Press `m` → Expected: both marks listed, each with `Files` = `1`

### Add the same mark twice is idempotent

**Preconditions:** `report.txt` carries `invoice`.

- [ ] Press `a`, type `invoice`, Enter → Expected: `Marked report.txt
      invoice.`; the `Marks:` line still shows `invoice` **once**
- [ ] Press `m` → Expected: `invoice` appears once, `Files` = `1` (not `2`)

### The same mark on several files

**Preconditions:** `invoice` exists on `report.txt`.

- [ ] Move to `notes.md`, press `a`, type `invoice`, Enter → Expected:
      `Marked notes.md invoice.`
- [ ] Press `m` → Expected: `invoice` listed once with `Files` = `2`

### Remove a mark from a file

**Preconditions:** `report.txt` and `notes.md` both carry `invoice`.

- [ ] Cursor on `report.txt`, press `x` → Expected: a modal reading `Mark to
      remove:`
- [ ] Type `invoice`, Enter → Expected: status reads `Took invoice off
      report.txt.`; the `Marks:` line no longer lists `invoice`
- [ ] Press `m` → Expected: `invoice` still listed, `Files` = `1`

### Removing the last use of a mark deletes the mark

**Preconditions:** only `notes.md` carries `invoice`.

- [ ] Cursor on `notes.md`, press `x`, type `invoice`, Enter → Expected: `Took
      invoice off notes.md.`
- [ ] Press `m` → Expected: `invoice` is **gone** from the marks screen; if it
      was the only mark, `No marks yet. Put one on a file from the files
      screen.`

### Removing a mark that does not exist

**Preconditions:** no mark named `nonexistent`.

- [ ] Cursor on any file, press `x`, type `nonexistent`, Enter → Expected: the
      status line shows the error `No mark is named 'nonexistent'.` — not a
      success message and not a traceback
- [ ] Confirm the file's `Marks:` line is unchanged

### Removing a mark the file does not carry

**Preconditions:** `invoice` exists but is carried only by `notes.md`; cursor
on `report.txt`.

- [ ] Press `x`, type `invoice`, Enter → Expected: the operation succeeds
      silently and reports `Took invoice off report.txt.`
- [ ] Press `m` → Expected: `invoice` still exists with `Files` = `1` — nothing
      was actually removed
- [ ] **Flag for review:** the success message is misleading here; confirm this
      is acceptable

---

## Mark Name Validation

Each of these starts from the files screen with the cursor on any file.

### Blank mark name is rejected

- [ ] Press `a`, press Enter on the empty input → Expected: status reads
      `A mark name cannot be blank.`; no mark is created
- [ ] Press `a`, type three spaces, Enter → Expected: the same message
- [ ] Press `m` → Expected: no blank-named mark appears

### Surrounding whitespace is trimmed

- [ ] Press `a`, type `  urgent  ` (leading and trailing spaces), Enter →
      Expected: `Marked <path> urgent.` — the reported name has no padding
- [ ] Press `m` → Expected: the mark is listed as `urgent`
- [ ] Press `escape`, press `a`, type `urgent` (no spaces), Enter → Expected:
      the mark count stays `1` — it is the same mark, not a second one

### Whitespace inside a mark name is rejected

- [ ] Press `a`, type `two words`, Enter → Expected: `A mark name cannot
      contain whitespace: 'two words'.`; no mark created
- [ ] Press `a`, type `tab\there` (with a real tab) → Expected: rejected the
      same way

### Reserved characters are rejected

- [ ] Press `a`, type `a:b`, Enter → Expected: `A mark name cannot contain ':':
      'a:b'.`
- [ ] Press `a`, type `a,b`, Enter → Expected: `A mark name cannot contain ',':
      'a,b'.`
- [ ] Press `a`, type `a:b,c`, Enter → Expected: the message names **both**
      characters, `',:'`

### Mark name length boundary

- [ ] Press `a`, paste a name of exactly **64** characters, Enter → Expected:
      accepted; `Marked <path> <name>.`
- [ ] Press `a`, paste a name of **65** characters, Enter → Expected: `A mark
      name cannot exceed 64 characters.`; no mark created
- [ ] Press `m` → Expected: only the 64-character mark is listed

### Mark names are case-sensitive

- [ ] Press `a`, type `Invoice`, Enter → Expected: accepted
- [ ] Press `a`, type `invoice`, Enter → Expected: accepted as a **separate**
      mark
- [ ] Press `m` → Expected: `Invoice` and `invoice` listed as two distinct
      rows

### Non-ASCII mark names

- [ ] Press `a`, type `ważne`, Enter → Expected: accepted and rendered
      correctly on the marks screen
- [ ] Press `a`, type an emoji such as `📌`, Enter → Expected: accepted (no
      rule forbids it); confirm it renders without breaking the table layout

### Cancelling the mark prompt

- [ ] Press `a`, type `something`, press `escape` → Expected: the modal closes;
      **no** mark is added; the status line is unchanged
- [ ] Press `m` → Expected: `something` does not appear

---

## Stacking Files

### Put a file in a stack

**Preconditions:** files screen, cursor on `a.jpg`, no stacks exist.

- [ ] Press `s` → Expected: a modal reading `Stack to put it in:`
- [ ] Type `Summer 2026`, Enter → Expected: status reads `Put a.jpg in Summer
      2026.`; the `Stack:` line reads `Stack: Summer 2026`
- [ ] Press `t` → Expected: the stacks screen lists `Summer 2026` with `Files`
      = `1`, and below the table `In Summer 2026:` followed by `a.jpg`

### A file sits in at most one stack

**Preconditions:** `a.jpg` sits in `Summer 2026`.

- [ ] Cursor on `a.jpg`, press `s`, type `Winter`, Enter → Expected: `Put a.jpg
      in Winter.`; the `Stack:` line reads `Stack: Winter`
- [ ] Press `t` → Expected: `Winter` holds `1` file; `Summer 2026` is **gone**
      (it was emptied and dropped)

### Moving a file out of a shared stack keeps the stack

**Preconditions:** `a.jpg` and `b.jpg` both sit in `Winter`.

- [ ] Cursor on `a.jpg`, press `s`, type `Spring`, Enter → Expected: `Put a.jpg
      in Spring.`
- [ ] Press `t` → Expected: `Spring` = `1`, `Winter` = `1`; both stacks survive
- [ ] Move the cursor between the two rows → Expected: the contents block
      updates to `In Spring:` / `a.jpg` and `In Winter:` / `b.jpg`

### Putting a file in the stack it already sits in

**Preconditions:** `a.jpg` sits in `Spring`.

- [ ] Press `s`, type `Spring`, Enter → Expected: `Put a.jpg in Spring.`; no
      change to the stack list
- [ ] Press `t` → Expected: `Spring` still holds `1` file and still exists (it
      was not emptied and re-created)

### Take a file out of its stack

**Preconditions:** `a.jpg` sits in `Spring` alone.

- [ ] Cursor on `a.jpg`, press `u` → Expected: **no prompt appears**; status
      reads `Took a.jpg out of its stack.`; the `Stack:` line reads `Stack:
      none`
- [ ] Press `t` → Expected: `Spring` is gone; if it was the last stack,
      `No stacks yet. Put a file in one from the files screen.`

### Taking an unstacked file out of a stack

**Preconditions:** cursor on a file with `Stack: none`.

- [ ] Press `u` → Expected: status reads `Took <path> out of its stack.` and
      nothing changes; no crash
- [ ] Press `t` → Expected: the stack list is unchanged

### Cancelling the stack prompt

- [ ] Press `s`, type `Autumn`, press `escape` → Expected: the modal closes; no
      stack is created; the file's `Stack:` line is unchanged
- [ ] Press `t` → Expected: `Autumn` does not appear

---

## Stack Name Validation

### Blank stack name is rejected

- [ ] Press `s`, press Enter on the empty input → Expected: `A stack name
      cannot be blank.`
- [ ] Press `s`, type only spaces, Enter → Expected: the same message

### Whitespace inside a stack name is allowed and collapsed

- [ ] Press `s`, type `  Summer    2026  `, Enter → Expected: `Put <path> in
      Summer 2026.` — ends trimmed, the internal run collapsed to one space
- [ ] Press `t` → Expected: exactly one stack named `Summer 2026`
- [ ] Return, press `s`, type `Summer 2026`, Enter → Expected: it resolves to
      the **same** stack, not a second lookalike
- [ ] Press `s`, type a name containing a tab or newline between words →
      Expected: also collapsed to a single space

### Stack name length boundary

- [ ] Press `s`, paste a name of exactly **255** characters, Enter → Expected:
      accepted
- [ ] Press `s`, paste a name of **256** characters, Enter → Expected: `A stack
      name cannot exceed 255 characters.`; no stack created

### Stack names are case-sensitive

- [ ] Put one file in `Archive` and another in `archive` → Expected: the stacks
      screen lists both as separate rows

---

## Filtering on the Files Screen

### Cycle the root filter

**Preconditions:** both roots scanned, several files under each.

- [ ] Press `f`, read the filter line → Expected: `Showing: all roots, any
      mark, any stack`
- [ ] Press `r` → Expected: the filter line names the first root alias
      (`docs`); only `docs` files are listed
- [ ] Press `r` again → Expected: `photos`; only `photos` files listed
- [ ] Press `r` again → Expected: back to `all roots`; every file listed again
- [ ] Confirm there is **no** "unrooted" step in the cycle

### Cycle the mark filter

**Preconditions:** marks `invoice` (on 2 files) and `draft` (on 1 file) exist;
at least one file carries no mark.

- [ ] Press `k` → Expected: the filter line's mark segment names the first mark
      alphabetically (`draft`); only files carrying `draft` are listed
- [ ] Press `k` → Expected: `invoice`; only its two files listed
- [ ] Press `k` → Expected: `unmarked`; only files carrying **no** mark listed
- [ ] Press `k` → Expected: back to `any mark`; every file listed

### Cycle the stack filter

**Preconditions:** stacks `Spring` and `Winter` exist; at least one file sits
in no stack.

- [ ] Press `c` → Expected: the filter's stack segment names `Spring`; only its
      files listed
- [ ] Press `c` → Expected: `Winter`
- [ ] Press `c` → Expected: `unstacked`; only files with `Stack: none` listed
- [ ] Press `c` → Expected: back to `any stack`

### Filters combine

**Preconditions:** a `docs` file carrying `invoice` and sitting in `Spring`; a
`photos` file carrying `invoice` but in no stack.

- [ ] Press `r` until the filter reads `docs`
- [ ] Press `k` until it reads `invoice`
- [ ] Press `c` until it reads `Spring`
- [ ] Read the filter line → Expected: `Showing: docs, invoice, Spring`
- [ ] Read the table → Expected: only the one file matching **all three**
      narrowings

### Empty-state message distinguishes "nothing indexed" from "nothing matches"

**Preconditions:** files are indexed.

- [ ] Cycle filters to a combination that matches nothing (e.g. root `photos`
      + mark `invoice` where no photo carries it) → Expected: the table is
      hidden and the message reads `No files match this filter.`
- [ ] Cycle every filter back to its unnarrowed step → Expected: the full
      listing returns
- [ ] Now clear the index (delete the db, restart, do not scan), press `f` →
      Expected: the message reads `No files indexed. Scan a root first.`

### Mark filter survives its mark being deleted

**Preconditions:** mark `solo` is carried by exactly one file.

- [ ] Press `k` until the filter reads `solo` → Expected: one file listed
- [ ] With the cursor on it, press `x`, type `solo`, Enter → Expected: `Took
      solo off <path>.`; the mark is now deleted (nothing carries it)
- [ ] Press `k` → Expected: no crash; the cycle **restarts** from the first
      step rather than raising, and the filter line shows a valid label
- [ ] Keep pressing `k` → Expected: the cycle steps through the remaining marks
      normally

### Cycling the mark filter with no marks at all

**Preconditions:** files indexed, zero marks exist.

- [ ] Press `k` → Expected: the filter goes to `unmarked` and lists every file
      (all are unmarked)
- [ ] Press `k` again → Expected: back to `any mark`; no crash

### Cycling the root filter with no roots

**Preconditions:** config with no roots.

- [ ] Press `f`, then `r` → Expected: nothing happens, no crash, the filter
      line is unchanged

### A newly configured root appears in the filter cycle

**Preconditions:** the app is running; the root filter has been cycled at least
once.

- [ ] Note that `r` cycles through the roots currently configured
- [ ] Confirm the root list is re-read on each `r` press → Expected: the cycle
      reflects the roots in the index at that moment

---

## Table Refresh Behaviour

### The listing does not re-filter after a mark change

**Preconditions:** the mark filter is set to `invoice`; the listed files all
carry it.

- [ ] Cursor on one listed file, press `x`, type `invoice`, Enter → Expected:
      status reads `Took invoice off <path>.` and the `Marks:` line updates
- [ ] Look at the table → Expected: the row is **still listed**, because the
      table is only refilled when a filter key is pressed
- [ ] Press `k` twice to cycle back to `invoice` → Expected: the row is now
      gone from the listing
- [ ] **Flag for review:** confirm this stale-row behaviour is intended rather
      than a bug

### Screen data is re-read on each visit

**Preconditions:** on the files screen.

- [ ] Add a new mark to a file, then press `m` → Expected: the marks screen
      shows the new mark
- [ ] Press `escape` back, remove that mark, press `m` again → Expected: the
      marks screen reflects the removal — each visit re-reads

---

## Marks Screen

### Empty marks screen

**Preconditions:** no marks exist.

- [ ] Press `m` from any screen → Expected: `No marks yet. Put one on a file
      from the files screen.`; the table is hidden
- [ ] Press `escape` → Expected: back to the previous screen

### Marks are listed with counts, ordered by name

**Preconditions:** marks `zulu` (1 file), `alpha` (3 files), `mike` (2 files).

- [ ] Press `m` → Expected: columns `Mark` and `Files`; rows in the order
      `alpha`, `mike`, `zulu`
- [ ] Read the counts → Expected: `3`, `2`, `1` respectively

### Marks orphaned by a scan still appear with a zero count

**Preconditions:** `report.txt` is the only file carrying `orphan`.

- [ ] In another terminal, `rm /tmp/qa/docs/report.txt`
- [ ] On the roots screen, cursor on `docs`, press `s` → Expected: `docs:
      0 added, 1 removed, 0 updated.`
- [ ] Press `m` → Expected: `orphan` is **still listed**, with `Files` = `0` —
      the scan cascaded the file-mark link away but left the mark itself
- [ ] **Flag for review:** the marks screen is documented as "marks in use";
      confirm a zero-count leftover is acceptable

---

## Stacks Screen

### Empty stacks screen

**Preconditions:** no stacks exist.

- [ ] Press `t` → Expected: `No stacks yet. Put a file in one from the files
      screen.`; the table is hidden
- [ ] Confirm no contents label or contents block is populated
- [ ] Press `escape` → Expected: back to the previous screen

### Stacks are listed with counts and contents

**Preconditions:** `Spring` holds 2 files, `Winter` holds 1.

- [ ] Press `t` → Expected: columns `Stack` and `Files`; rows ordered by name,
      `Spring` then `Winter`
- [ ] With the cursor on the first row → Expected: `In Spring:` above a list of
      its two relative paths, one per line
- [ ] Arrow down to `Winter` → Expected: the label becomes `In Winter:` and the
      contents show its single path
- [ ] Arrow back up to `Spring` → Expected: its contents reappear correctly
      (they are cached per stack; confirm the cache returns the right set)

### Stack contents show paths from every root

**Preconditions:** a stack holding one `docs` file and one `photos` file.

- [ ] Press `t`, cursor on that stack → Expected: both relative paths are
      listed; note that the root alias is **not** shown, so two files with the
      same relative path under different roots look identical
- [ ] **Flag for review:** confirm ambiguous paths in the contents block are
      acceptable

### Stacks orphaned by a scan still appear with a zero count

**Preconditions:** one file sits in stack `lonely`, and it is the only one.

- [ ] Delete that file from disk and rescan its root → Expected: `0 added,
      1 removed, 0 updated.`
- [ ] Press `t` → Expected: `lonely` is still listed with `Files` = `0` and
      contents `(nothing)`
- [ ] **Flag for review:** same question as for orphaned marks

---

## Navigation

### Global bindings work from every screen

**Preconditions:** app running on the roots screen.

- [ ] Press `f` → files screen; `escape` → roots screen
- [ ] Press `m` → marks screen; `escape` → roots screen
- [ ] Press `t` → stacks screen; `escape` → roots screen
- [ ] From the files screen press `m` → Expected: the marks screen opens
- [ ] From the marks screen press `t` → Expected: the stacks screen opens

### Escape from the roots screen

**Preconditions:** on the roots screen with no screen pushed above it.

- [ ] Press `escape` → Expected: nothing happens; the app does **not** quit or
      raise a "screen stack empty" error

### Screens stack up when pushed repeatedly

**Preconditions:** on the roots screen.

- [ ] Press `f`, `f`, `f` → Expected: three files screens are pushed; the
      display looks the same each time
- [ ] Press `escape` three times → Expected: three pops are needed to return to
      the roots screen
- [ ] **Flag for review:** confirm the unbounded screen stack is acceptable, or
      whether repeated navigation should replace rather than push

### Quitting

- [ ] From any screen, press `q` → Expected: the app exits and the terminal is
      restored (no leftover raw mode, no garbled prompt)
- [ ] Press `q` while a name prompt modal is open → Expected: `q` is typed into
      the input rather than quitting the app; `escape` then closes the modal

### Key conflicts between screens

- [ ] On the **roots** screen press `s` → Expected: it starts a **scan**
- [ ] On the **files** screen press `s` → Expected: it opens the **stack**
      prompt
- [ ] Confirm neither key leaks into the other screen's behaviour

---

## Data Integrity & Persistence

### Everything survives a restart

**Preconditions:** roots scanned; several marks applied; a couple of stacks
populated.

- [ ] Note the exact contents of the marks and stacks screens
- [ ] Press `q`, then run `acre` again
- [ ] Press `f` → Expected: the same files listed, with the same sizes
- [ ] Press `m` → Expected: the same marks and counts
- [ ] Press `t` → Expected: the same stacks, counts and contents
- [ ] Pick a file that carried marks and check its `Marks:` line → Expected:
      unchanged

### Removing a root from the config drops its files

**Preconditions:** both roots scanned; a `photos` file carries a mark and sits
in a stack.

- [ ] Quit the app; delete the `photos = …` line from the config; run `acre`
- [ ] Read the roots screen → Expected: only `docs` is listed
- [ ] Press `f` → Expected: no `photos` files remain in the listing
- [ ] Press `m` → Expected: a mark only `photos` files carried now shows
      `Files` = `0` (or is absent if it never existed)
- [ ] Confirm the `docs` files, marks and stacks are untouched
- [ ] Check the database has no dangling rows: `sqlite3 <db_path> "SELECT
      COUNT(*) FROM files WHERE root_id NOT IN (SELECT id FROM roots);"` →
      Expected: `0`
- [ ] Also check `file_marks`: `SELECT COUNT(*) FROM file_marks WHERE file_id
      NOT IN (SELECT id FROM files);` → Expected: `0`

### Re-adding a removed root re-indexes it from scratch

**Preconditions:** the previous scenario left `photos` out of the config.

- [ ] Quit, put `photos` back in the config, run `acre`
- [ ] Read the roots screen → Expected: `photos` is listed again
- [ ] Press `f` → Expected: **no** photos files yet (the index was dropped, not
      preserved)
- [ ] Scan `photos` → Expected: every file re-added; the marks and stack
      membership they had before are **not** restored

### Changing a root's path updates it in place

**Preconditions:** `docs` scanned and its files carry marks.

- [ ] Quit; in another terminal, `mv /tmp/qa/docs /tmp/qa/documents`; change
      the config to `docs = "/tmp/qa/documents"`; run `acre`
- [ ] Read the roots screen → Expected: `docs` is listed with the **new** path
- [ ] Press `f` → Expected: the previously indexed files are **still there**
      with their marks intact (the root row was updated, not replaced)
- [ ] Scan `docs` → Expected: `0 added, 0 removed, 0 updated.` — the same files
      are found under the new path

### Renaming a root's alias is a delete plus an insert

**Preconditions:** `docs` scanned with marks applied.

- [ ] Quit; rename the alias in the config from `docs` to `documents` (path
      unchanged); run `acre`
- [ ] Read the roots screen → Expected: only `documents` is listed
- [ ] Press `f` → Expected: **no** files listed — the old root and its index
      were dropped
- [ ] Scan `documents` → Expected: every file re-added, but the marks and stack
      membership are gone
- [ ] **Flag for review:** confirm that an alias rename losing all marks is the
      intended trade-off

### Foreign keys are actually enforced

**Preconditions:** a populated database; the app is **not** running.

- [ ] Run `sqlite3 <db_path> "PRAGMA foreign_keys;"` → note that this is a
      per-connection setting; the app turns it on at connect
- [ ] Run `sqlite3 <db_path> "PRAGMA foreign_key_check;"` → Expected: no output
      (no violations)
- [ ] Run `sqlite3 <db_path> "PRAGMA journal_mode;"` → Expected: `wal`
- [ ] Confirm a `-wal` file exists alongside the db while the app runs

### A failed operation leaves nothing half-written

**Preconditions:** files indexed.

- [ ] Press `a`, submit an invalid name (e.g. `bad name`) → Expected: the error
      is reported
- [ ] Press `m` → Expected: no partially created mark named `bad` or `bad name`
- [ ] Query the database directly: `sqlite3 <db_path> "SELECT * FROM marks;"` →
      Expected: only the valid marks

### Two instances against the same database

**Preconditions:** a populated index.

- [ ] Open `acre` in two terminals
- [ ] In terminal A, add a mark to a file → Expected: it succeeds
- [ ] In terminal B, press `m` → Expected: the new mark is visible (the screen
      re-reads on each visit)
- [ ] In terminal B, add a different mark; in terminal A press `m` → Expected:
      both marks visible, no "database is locked" error
- [ ] Start a long scan in terminal A and browse in terminal B → Expected: B
      stays responsive (WAL lets a reader run beside the writer)
- [ ] **Flag anything that reports `database is locked`**

---

## Filesystem Edge Cases

### Symlinks

**Preconditions:** the test tree contains `link-ok` (to a real file) and
`link-dead` (broken).

- [ ] Scan `docs`, press `f` → Expected: `link-ok` is listed as a file, with
      the size of its **target**
- [ ] Expected: `link-dead` is **not** listed and did not abort the scan
- [ ] Add a symlink to a directory (`ln -s sub linkdir`) and rescan → Expected:
      the scan completes; record whether files under `linkdir/` appear
      **twice** (once via `sub/`, once via `linkdir/`) and flag if duplication
      is not intended

### Hidden files and empty directories

- [ ] Scan `docs`, press `f` → Expected: `.hidden.txt` **is** indexed (nothing
      excludes dotfiles)
- [ ] Expected: `emptydir/` produces no row — directories are not files
- [ ] Expected: `empty.txt` is indexed with size `0`

### A file that vanishes mid-scan

**Preconditions:** a root with enough files that the scan takes a moment.

- [ ] Start a scan, and while it runs delete a file it has not reached yet →
      Expected: the scan completes without raising; the deleted file is simply
      not indexed
- [ ] Rescan → Expected: consistent counts, no phantom row

### Unreadable files and directories

**Preconditions:** `chmod 000 /tmp/qa/docs/secret.txt` and a `chmod 000`
subdirectory.

- [ ] Scan `docs` → Expected: the scan completes; the unreadable file is either
      indexed by its stat or skipped, but **no traceback**
- [ ] Confirm the rest of the tree is still indexed

### Deeply nested and long paths

- [ ] Create a path 10 directories deep and scan → Expected: the full relative
      path is indexed and rendered on the files screen
- [ ] Create a file whose relative path exceeds ~200 characters and scan →
      Expected: indexed without truncation or error

### A large root

**Preconditions:** a root with 10,000+ files.

- [ ] Scan it → Expected: it completes; note how long it takes and whether the
      UI stayed responsive throughout
- [ ] Press `f` → Expected: the files screen renders and scrolls without a
      noticeable stall
- [ ] Cycle the filters → Expected: each filter change returns in reasonable
      time

---

## Terminal Rendering

### Small terminal

- [ ] Resize the terminal to roughly 40x12 and open each screen → Expected: no
      crash; content clips or scrolls rather than corrupting the layout
- [ ] Open the name prompt in a small terminal → Expected: the prompt and input
      remain usable

### Resizing while running

- [ ] With the files screen open, resize the terminal wider and narrower →
      Expected: the table reflows; the filter, marks, stack and status lines
      stay readable

### Long status messages

- [ ] Trigger a status message with a long path and a long mark name →
      Expected: the line wraps or clips rather than pushing the footer off
      screen

---

## Regression Sweep (run before merge)

- [ ] `mise run lint:py` → Expected: passes clean
- [ ] `mise run test:py` → Expected: all tests pass
- [ ] Fresh install path: delete the db, run `acre`, scan both roots, apply two
      marks and one stack, quit, relaunch → Expected: everything persisted
- [ ] Every keybinding in the README's key table behaves as documented
- [ ] No screen shows a raw Python traceback under any scenario above
