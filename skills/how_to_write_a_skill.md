# How to Write a Skill

A skill is a markdown file in skills/ that teaches Pincer a specific behaviour or response pattern. Skills are loaded into the system prompt at startup.

## Format

Each skill file should have:
- A `# Title` heading
- Instructions written in second person ("When the user asks you to...")
- Concrete examples where helpful

## Creating a Skill

Ask Pincer to create a skill:
  "Create a skill for summarising articles"
  "Write a skill that teaches you how to write shell scripts"

Pincer will propose the skill content wrapped in [SAVE_SKILL: filename.md] and ask for confirmation before saving.

## Tips

- Keep skills focused on one behaviour
- Use clear, direct language
- Skills can reference other skills by name
- Overly long skills consume context — keep them under 200 lines
