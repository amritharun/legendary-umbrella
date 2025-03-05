import re


def sanitize_string(input_string: str) -> str:
    """Returns a sanitized version of the input string, removing all invalid characters and truncating to a max length of 50"""
    if not input_string:
        return ""

    trimmed = input_string.strip()
    sanitized = re.sub(r"[^a-zA-Z0-9- ,]", "", trimmed)
    return sanitized[:50]
