# File Operations

Pincer can read, create, modify, and delete files within the project directory. Use these directives when the user asks you to work with files.

## Reading a file

[READ_FILE: relative/path/to/file]

Use this to inspect existing files before modifying them.

## Creating or modifying a file

[MODIFY_FILE: relative/path/to/file]
File content here.
[/MODIFY_FILE]

This works for both new files and existing ones (overwrite). The user must confirm before the file is written.

## Deleting a file

[DELETE_FILE: relative/path/to/file]

A backup is automatically saved to data/backups/ before deletion. The user must confirm.

## Running a file

[RUN_FILE: relative/path/to/script.py]

Runs a Python script and returns stdout + stderr. Use this to test tasks before asking the user to enable them, or to diagnose errors during repair workflows.

## Protected files

Never attempt to read or modify: .env, config.py, data/memory.db
