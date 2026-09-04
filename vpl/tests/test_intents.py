"""Navigation intent resolution."""

from __future__ import annotations

from construct_zero_vpl.intents import IntentKind, is_navigation_intent, parse_intent
from construct_zero_vpl.models import Bucket, ListItem, SourceSpan


def _bucket(label: str) -> Bucket:
    return Bucket(
        id="b0",
        label=label,
        items=[
            ListItem(id="i1", text="item one", span=SourceSpan(start=0, end=8)),
        ],
    )


def test_repeat_and_read_all():
    assert parse_intent("repeat").kind == IntentKind.REPEAT
    assert parse_intent("read all").kind == IntentKind.READ_ALL


def test_ordinal_bucket_choice():
    buckets = [_bucket("workflow fixes"), _bucket("ui polish")]
    intent = parse_intent("second", buckets)
    assert intent.kind == IntentKind.CHOOSE_BUCKET
    assert intent.bucket_index == 1


def test_fuzzy_label_match():
    buckets = [_bucket("MediaRecorder finalize"), _bucket("session TTL")]
    intent = parse_intent("mediarecorder", buckets)
    assert intent.kind == IntentKind.CHOOSE_BUCKET
    assert intent.bucket_index == 0


def test_new_question_default():
    assert not is_navigation_intent("What is the weather in Paris?")
