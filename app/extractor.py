
import re


ORDER_RE = re.compile(r"\bORD[- #]?[A-Z0-9]{3,}\b", re.IGNORECASE)

SKU_RE = re.compile(
    r"\bSKU[- #]?([A-Z0-9][A-Z0-9-]*)\b",
    re.IGNORECASE,
)

PRODUCT_CODE_RE = re.compile(
    r"\bPRODUCT(?:\s+(?:ID|CODE))?[- #:=]+([A-Z0-9][A-Z0-9-]*)\b",
    re.IGNORECASE,
)

DEADLINE_PATTERNS = (
    (re.compile(r"\bbefore (?:my|the) invoice closes tomorrow\b", re.I),
     "Before invoice closes tomorrow"),
    (re.compile(r"\bbefore (?:my|the) invoice closes\b", re.I),
     "Before invoice closes"),
    (re.compile(r"\bwithin (?:one|an) hour\b", re.I), "Within one hour"),
    (re.compile(r"\bin one hour\b", re.I), "Within one hour"),
    (re.compile(r"\bimmediately\b|\bright away\b", re.I), "Immediately"),
    (re.compile(r"\basap\b", re.I), "ASAP"),
    (re.compile(r"\btoday\b", re.I), "Today"),
    (re.compile(r"\btonight\b", re.I), "Tonight"),
    (re.compile(r"\btomorrow\b", re.I), "Tomorrow"),
    (re.compile(r"\bnext week\b", re.I), "Next week"),
    (re.compile(r"\bnext month\b", re.I), "Next month"),
)


def extract_fields(text: str) -> dict:
    order = ORDER_RE.search(text)
    sku = SKU_RE.search(text)
    product = PRODUCT_CODE_RE.search(text)

    if sku:
        product_id = f"SKU-{sku.group(1)}"
    elif product:
        product_id = product.group(1)
    else:
        product_id = None

    deadline = next(
        (label for pattern, label in DEADLINE_PATTERNS if pattern.search(text)),
        None,
    )

    return {
        "order_id": order.group(0).replace(" ", "-") if order else None,
        "product_id": product_id,
        "deadline": deadline,
    }
