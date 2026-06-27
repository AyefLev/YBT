import re


def normalize_generated_math_text(content: str) -> str:
    """Convert common inline LaTeX from LLM output into readable plain text."""
    if not content:
        return content

    pattern = re.compile(r"\[(公式|SVG)\]([\s\S]*?)\[/\1\]", re.IGNORECASE)
    parts: list[str] = []
    last_index = 0
    for match in pattern.finditer(content):
        parts.append(_normalize_inline_latex(content[last_index : match.start()]))
        parts.append(match.group(0))
        last_index = match.end()
    parts.append(_normalize_inline_latex(content[last_index:]))
    return "".join(parts)


def _normalize_inline_latex(value: str) -> str:
    value = re.sub(r"\\\(([\s\S]*?)\\\)", r"\1", value)
    value = re.sub(r"\\\[([\s\S]*?)\\\]", r"\1", value)
    value = re.sub(r"\\mathrm\{([^{}]+)\}", r"\1", value)
    value = re.sub(r"\\operatorname\{([^{}]+)\}", r"\1", value)
    value = re.sub(r"\\text\{([^{}]+)\}", r"\1", value)
    value = re.sub(r"\\mathbf\{([^{}]+)\}", r"\1", value)
    value = re.sub(r"\\mathit\{([^{}]+)\}", r"\1", value)

    replacements = {
        r"\times": "×",
        r"\cdot": "·",
        r"\div": "÷",
        r"\leq": "≤",
        r"\geq": "≥",
        r"\neq": "≠",
        r"\in": "∈",
        r"\sum": "Σ",
        r"\left": "",
        r"\right": "",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)

    value = re.sub(r"_\{([^{}]+)\}", r"_\1", value)
    value = re.sub(r"\^\{([^{}]+)\}", r"^\1", value)
    value = value.replace(r"\{", "{").replace(r"\}", "}")
    value = value.replace(r"\[", "").replace(r"\]", "")
    value = value.replace(r"\(", "").replace(r"\)", "")
    value = re.sub(r"\\([A-Za-z]+)", r"\1", value)
    value = re.sub(r"[ \t]+", " ", value)
    return value
