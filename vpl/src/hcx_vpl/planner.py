"""Extractive speak-text builders (verbatim spans only)."""

from __future__ import annotations

from hcx_vpl.models import Bucket, ListItem, SpeechDocument
from hcx_vpl.renderer import first_sentence, render_for_speech


def orient_and_map_text(doc: SpeechDocument) -> str:
    n_items = len(doc.items)
    n_buckets = len(doc.buckets)
    parts: list[str] = []

    if doc.intro:
        parts.append(first_sentence(doc.intro, max_chars=180))

    if n_items and n_buckets:
        parts.append(
            f"I found {n_items} suggestions in {n_buckets} groups. "
            "The full list is on your screen."
        )
    elif n_items:
        parts.append(
            f"I found {n_items} suggestions. The full list is on your screen."
        )

    if doc.buckets:
        labels = [render_for_speech(b.label) for b in doc.buckets[:4]]
        if labels:
            joined = ", ".join(labels[:-1]) + f", and {labels[-1]}" if len(labels) > 1 else labels[0]
            parts.append(f"The groups are: {joined}.")
        parts.append("Which group should we open? You can also say read all.")

    return " ".join(p for p in parts if p).strip()


def bucket_summary(bucket: Bucket, bucket_num: int, total: int) -> str:
    count = len(bucket.items)
    label = render_for_speech(bucket.label)
    intro = f"Group {bucket_num} of {total}: {label}. "
    if count == 1:
        intro += "It has one item. "
    else:
        intro += f"It has {count} items. "
    first = render_for_speech(bucket.items[0].text) if bucket.items else ""
    if first:
        intro += first_sentence(first, max_chars=200)
        if count > 1:
            intro += " Say next for more, or back for the menu."
    return intro.strip()


def item_text(item: ListItem, *, partial: bool = True) -> str:
    body = render_for_speech(item.text)
    if partial and len(body) > 280:
        return first_sentence(body, max_chars=260) + " Say next for the rest."
    return body


def read_all_intro(doc: SpeechDocument) -> str:
    return (
        f"I'll read all {len(doc.items)} items. "
        "You can say stop anytime. The full text remains on your screen."
    )


def buckets_for_ui(doc: SpeechDocument) -> list[dict]:
    return [
        {"id": b.id, "label": render_for_speech(b.label), "count": len(b.items)}
        for b in doc.buckets
    ]


NAV_HINT = "Say a group name, first or second, read all, repeat, or back."
