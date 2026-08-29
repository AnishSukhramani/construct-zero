"""Navigation intent detection without LLM."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum

from hcx_vpl.models import Bucket


class IntentKind(str, Enum):
    NEW_QUESTION = "new_question"
    CHOOSE_BUCKET = "choose_bucket"
    NEXT = "next"
    BACK = "back"
    REPEAT = "repeat"
    STOP = "stop"
    READ_ALL = "read_all"


@dataclass
class ParsedIntent:
    kind: IntentKind
    bucket_index: int | None = None
    confidence: float = 1.0


_ORDINALS = {
    "first": 0,
    "one": 0,
    "1": 0,
    "second": 1,
    "two": 1,
    "2": 1,
    "third": 2,
    "three": 2,
    "3": 2,
    "fourth": 3,
    "four": 3,
    "4": 3,
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _fuzzy_bucket_index(text: str, buckets: list[Bucket]) -> int | None:
    if not buckets:
        return None
    best_idx = None
    best_score = 0.0
    for idx, bucket in enumerate(buckets):
        label = _normalize(bucket.label)
        if not label:
            continue
        if label in text or text in label:
            return idx
        score = SequenceMatcher(None, text, label).ratio()
        if score > best_score:
            best_score = score
            best_idx = idx
    if best_score >= 0.55:
        return best_idx
    return None


def parse_intent(user_text: str, buckets: list[Bucket] | None = None) -> ParsedIntent:
    text = _normalize(user_text)
    if not text:
        return ParsedIntent(IntentKind.NEW_QUESTION)

    if re.search(r"\b(stop|cancel|quit|done|never mind|nevermind)\b", text):
        return ParsedIntent(IntentKind.STOP)
    if re.search(r"\b(repeat|again|say that again|what did you say)\b", text):
        return ParsedIntent(IntentKind.REPEAT)
    if re.search(r"\b(read all|everything|full list|all of them|read everything)\b", text):
        return ParsedIntent(IntentKind.READ_ALL)
    if re.search(r"\b(next|continue|go on|more)\b", text):
        return ParsedIntent(IntentKind.NEXT)
    if re.search(r"\b(back|previous|go back|up)\b", text):
        return ParsedIntent(IntentKind.BACK)

    for word, idx in _ORDINALS.items():
        if re.search(rf"\b{re.escape(word)}\b", text):
            if buckets and idx < len(buckets):
                return ParsedIntent(IntentKind.CHOOSE_BUCKET, bucket_index=idx)

    if buckets:
        idx = _fuzzy_bucket_index(text, buckets)
        if idx is not None:
            return ParsedIntent(IntentKind.CHOOSE_BUCKET, bucket_index=idx)

    # Short utterances in nav context are often bucket picks
    if buckets and len(text.split()) <= 4:
        idx = _fuzzy_bucket_index(text, buckets)
        if idx is not None:
            return ParsedIntent(IntentKind.CHOOSE_BUCKET, bucket_index=idx)

    return ParsedIntent(IntentKind.NEW_QUESTION)


def is_navigation_intent(user_text: str, buckets: list[Bucket] | None = None) -> bool:
    return parse_intent(user_text, buckets).kind != IntentKind.NEW_QUESTION
