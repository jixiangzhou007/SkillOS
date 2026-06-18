"""System skills used by Create vs Agent dispatch modes (SD-compatible)."""


SYSTEM_SKILL_NAMES = frozenset({
    "brainstorming",
    "skill-creator",
    "deep-digest",
    "cold-start-interview",
})

CREATE_REFERENCE_SKILL = "skill-creator"
AGENT_DEFAULT_SKILL = "brainstorming"


def create_mode_skills(all_skills: list[str]) -> list[str]:
    """Create mode: all user skills + skill-creator, exclude brainstorming."""
    skills = [s for s in all_skills if s != AGENT_DEFAULT_SKILL]
    if CREATE_REFERENCE_SKILL not in skills:
        skills.append(CREATE_REFERENCE_SKILL)
    return skills


def agent_mode_skills(all_skills: list[str]) -> list[str]:
    """Agent mode: brainstorming only (optimize / analyze, not extract)."""
    if AGENT_DEFAULT_SKILL in all_skills:
        return [AGENT_DEFAULT_SKILL]
    return [AGENT_DEFAULT_SKILL]


def methodology_paste_instruction() -> str:
    """When user pastes long reference material in Agent mode."""
    return (
        "⚠️ 用户发送了一段参考学习资料。你的任务是判断处理方式，不是解释资料内容。\n"
        "必须用 [选项] 格式给出选择，不要直接讲解资料本身。\n"
        "[选项] 提取为知识条目 | extract_knowledge\n"
        "[选项] 优化 skill-creator 技能 | optimize_skill_creator\n"
        "[选项] 基于此创建新技能 | create_skill\n"
        "[选项] 只是聊天，不处理 | just_chat\n"
        "先一句话说明这是什么资料，然后只输出选项。"
    )
