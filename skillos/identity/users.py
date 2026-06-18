"""Platform user id normalization."""



def to_platform_user_id(user_id: str) -> str:
    if not user_id:
        return ""
    if user_id.startswith("usr_"):
        return user_id
    return f"usr_{user_id}"


def from_platform_user_id(platform_id: str) -> str:
    """Strip ``usr_`` for marketplace ``users.user_id`` lookup."""
    if platform_id.startswith("usr_"):
        return platform_id[4:]
    return platform_id
