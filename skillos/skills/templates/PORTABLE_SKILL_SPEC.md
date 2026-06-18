# Portable SKILL.md — installable in Cursor, Claude Code, Trae

Every conversation extraction must produce a skill a non-technical user can copy into:

- Cursor: `~/.cursor/skills/<tool_name>/SKILL.md`
- Claude Code: `~/.claude/skills/<tool_name>/SKILL.md`
- Trae: `~/.trae/skills/<tool_name>/SKILL.md`

## Required YAML (written by SkillOS on save)

```yaml
name: contract-review          # lowercase ASCII, hyphens, max 64 chars
description: >                 # third person; WHAT + WHEN + trigger terms
  Reviews sales contracts for price, warranty, liability, IP, and penalty clauses.
  Use when the user uploads a contract, asks to review terms, or mentions contract risk.
```

## Required body sections (executable on the ground)

1. **When to use** — plain language, no jargon
2. **Instructions** — numbered steps with if-then branches (from S_body)
3. **Decision routes** — S_route table
4. **Inputs** — S_params with types and defaults

Do not bury steps in prose. Each step = one action the agent can execute.

## Rules

- User never needs to know the word "skill" — conversation collects workflow only
- Do not invent steps not confirmed in dialogue; mark gaps `[待确认]`
- S_route required (≥2 rows)
- S_trigger must include keywords AND excludes (when NOT to use)
