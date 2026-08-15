# Marks and stacks

Both are made on the files screen, on the file under the cursor.

| Key | Does |
|-----|------|
| <kbd>a</kbd> | put a mark on the file — asks for a name |
| <kbd>x</kbd> | take a mark off the file — asks for a name |
| <kbd>s</kbd> | put the file in a stack — asks for a name |
| <kbd>u</kbd> | take the file out of its stack — asks nothing |

<kbd>Escape</kbd> at a prompt backs out and changes nothing.

## Marks

A mark is a label, and the relationship runs both ways without limit: a file
carries any number of marks, and a mark sits on any number of files.

Adding one that does not exist creates it. Adding one a file already carries
changes nothing and is not an error, so you can mark the same file twice without
thinking about it.

### Names

A mark name is trimmed of surrounding whitespace, then must:

- be non-empty
- be at most **64 characters**
- contain **no whitespace at all** — `tax return` is rejected, `tax-return` and
  `tax_return` are fine
- avoid `:` and `,`, which separate marks from one another when they are listed

Case is kept and case matters: `Invoice` and `invoice` are two different marks,
in the same way two files can differ only by case.

A name that breaks a rule is reported in the status line and nothing is written:

```text
A mark name cannot contain whitespace: 'tax return'.
```

### When a mark disappears

Take the last file off a mark and the mark is deleted. The marks screen is
therefore a list of marks in use, not a catalogue of every mark you have ever
typed. There is no way to create an empty mark and no need to retire one.

The exception is a mark whose files vanished from under it — dropped by a scan,
or by a root leaving the config. That mark stays listed with a file count of
zero, because nothing was taken off it; it was the files that went. Marking and
unmarking any file with that name clears it out.

## Stacks

A stack is a named group, and a file sits in **at most one**. This is the whole
difference from a mark: putting a file in a stack takes it out of the stack it
was in, rather than adding to it. Putting a file in the stack it is already in
changes nothing.

Because the move empties the old stack when that file was the last one in it,
the old stack is then deleted — the same rule as for marks, and the stacks
screen is likewise a list of stacks holding something.

### Names

A stack name has runs of whitespace collapsed to single spaces and the ends
trimmed, so `" Summer   2026 "` and `"Summer 2026"` are the same stack rather
than two that look alike. It must be non-empty and at most **255 characters**.

Spaces are allowed, unlike in a mark name: a file has only one stack, so a stack
name is never listed beside others and never has to be split apart again. Case
is kept and case matters, as with marks.

## Which one to use

Reach for a **mark** when a file can reasonably be several things at once —
`invoice`, `2025`, `unpaid`, `scanned`. Marks accumulate, and the files screen
filters by one at a time.

Reach for a **stack** when membership is exclusive and you want to see the group
as a whole — a batch you are working through, a set you are about to burn to a
disc, a client a document belongs to. The stacks screen lists each stack with
its size and shows you the paths inside the one under the cursor.

Nothing stops you using both on the same file, and the files screen filters on
root, mark and stack together.
