"""Classify ingested content as actionable (how-to) vs conceptual (reference)."""



def classify_content(text: str) -> str:
    """Return ``actionable`` or ``conceptual``."""
    try:
        from skillos.llm_client import call

        prompt = f"""判断以下内容是"actionable"(含可执行步骤/方法论/流程/How-to)还是"conceptual"(概念/背景/参考/理论)?

内容: {text[:500]}

只回复一个词: actionable 或 conceptual"""
        result = call(prompt, max_tokens=10, temperature=0.1).strip().lower()
        return "actionable" if "actionable" in result else "conceptual"
    except Exception:
        return "conceptual"
