# Hermes Agent Integration

SkillOS is designed to run alongside Hermes Agent. When Hermes is installed,
SkillOS acts as the knowledge engineering layer; Hermes handles execution.

## Quick Start (Standalone)

```bash
cd SkillOS
pip install -e .
skillos                    # Desktop app
skillos --server-only      # API server only (headless)
```

## Quick Start (With Hermes)

```bash
# 1. Install Hermes Agent
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# 2. Install SkillOS
cd SkillOS
pip install -e .

# 3. Link SkillOS skills to Hermes
skillos link-hermes

# 4. Skills created in SkillOS now appear in Hermes
#    Skills executed in Hermes feed traces back to SkillOS
```

## Architecture

```
┌──────────────────────────────────────────────┐
│                  SkillOS                      │
│                                               │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Knowledge │  │ Evolution│  │ Marketplace │  │
│  │ Pipeline  │  │ Engine   │  │   (Hub)     │  │
│  └─────┬─────┘  └────┬─────┘  └──────┬──────┘  │
│        │              │               │         │
│  ┌─────┴──────────────┴───────────────┴──────┐  │
│  │         hermes_bridge.py                   │  │
│  │  SkillOS ↔ agentskills.io format          │  │
│  └──────────────────┬────────────────────────┘  │
└─────────────────────┼───────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────┐
│              Hermes Agent                        │
│  ┌──────────────────┴──────────────────────────┐ │
│  │  Skill execution, multi-platform messaging,  │ │
│  │  memory system, sub-agents, automation       │ │
│  └──────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

## When Hermes Is Not Installed

SkillOS runs independently with degraded execution capabilities:
- Skills can be created, evolved, and published
- Knowledge pipeline works fully
- Marketplace works fully
- Skill execution uses built-in agent_factory (no Hermes runtime)

## What Hermes Adds

- Multi-platform deployment (Telegram, Discord, Slack, etc.)
- Native desktop app shell (replace pywebview)
- Production-grade sub-agent system
- FTS5 memory for conversation search
- Built-in cron scheduler for automations
- 200+ model provider support via OpenRouter
