
import re


def summarize(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()

    if len(cleaned) <= 220:
        return cleaned

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)

    if len(sentences) >= 2:
        result = " ".join(sentences[:2])
    else:
        result = cleaned[:217].rstrip() + "..."

    return result[:300]
