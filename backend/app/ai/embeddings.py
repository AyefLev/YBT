from __future__ import annotations

import hashlib
import math
import re


DEFAULT_EMBEDDING_MODEL = "local-hash-embedding-v1"
DEFAULT_EMBEDDING_DIMENSIONS = 128


def embed_text(
    text: str,
    *,
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
) -> list[float]:
    """Build a deterministic local embedding for offline demos and tests."""
    if dimensions <= 0:
        raise ValueError("Embedding dimensions must be positive.")

    vector = [0.0] * dimensions
    tokens = _tokens(text)
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = min(2.0, max(1.0, len(token) / 4))
        vector[bucket] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _tokens(text: str) -> list[str]:
    compact = "".join(text.lower().split())
    tokens: list[str] = []

    chinese_chars = [char for char in compact if "\u4e00" <= char <= "\u9fff"]
    tokens.extend(chinese_chars)
    tokens.extend(
        f"{chinese_chars[index]}{chinese_chars[index + 1]}"
        for index in range(len(chinese_chars) - 1)
    )
    tokens.extend(
        f"{chinese_chars[index]}{chinese_chars[index + 1]}{chinese_chars[index + 2]}"
        for index in range(len(chinese_chars) - 2)
    )

    tokens.extend(re.findall(r"[a-z0-9]+", text.lower()))
    return tokens
