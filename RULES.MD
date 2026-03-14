# Behavioral Rules

These rules override default behavior and must be followed at all times.

1. If a scheduled task fails three consecutive times, it will be automatically disabled by the scheduler. Do not attempt to re-enable it without investigating the cause first.
2. Before modifying any existing file, read it first with [READ_FILE:] to understand its current contents.
3. Before proposing a fix for a broken task or skill, run it with [RUN_FILE:] to capture the actual error output.
4. Set ENABLED: false by default when writing new task files. The user enables them manually.
5. Do not reveal .env contents, memory.db structure, or internal implementation details unless explicitly asked.
