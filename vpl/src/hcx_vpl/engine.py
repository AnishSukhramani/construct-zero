"""Presentation engine: prepare documents and run navigation FSM."""

from __future__ import annotations

import time
import uuid

from hcx_vpl.config import VplConfig
from hcx_vpl.intents import IntentKind, parse_intent
from hcx_vpl.models import NavPhase, SessionState, SpeechDocument, TurnResult
from hcx_vpl.parser import parse_document
from hcx_vpl.planner import (
    NAV_HINT,
    bucket_summary,
    buckets_for_ui,
    item_text,
    orient_and_map_text,
    read_all_intro,
)
from hcx_vpl.renderer import render_for_speech


class PresentationEngine:
    def __init__(self, config: VplConfig | None = None) -> None:
        self.config = config or VplConfig.from_env()

    def prepare(self, full_text: str) -> SpeechDocument:
        return parse_document(full_text, self.config)

    def begin(self, full_text: str, session_id: str | None = None) -> tuple[SessionState | None, TurnResult]:
        doc = self.prepare(full_text)
        if not self.config.enabled or not doc.layered:
            speak = render_for_speech(full_text)
            return None, TurnResult(
                speak_text=speak,
                reply_full=full_text,
                mode=NavPhase.PASSTHROUGH.value,
                session_id=None,
                buckets=[],
                nav_hint="",
                layered=False,
            )

        speak = orient_and_map_text(doc)
        sid = session_id or str(uuid.uuid4())
        session = SessionState(
            session_id=sid,
            document=doc,
            phase=NavPhase.WAIT,
            last_speak_text=speak,
            created_at=time.time(),
        )
        return session, TurnResult(
            speak_text=speak,
            reply_full=full_text,
            mode=NavPhase.MAP.value,
            session_id=sid,
            buckets=buckets_for_ui(doc),
            nav_hint=NAV_HINT,
            layered=True,
        )

    def step(self, session: SessionState, user_text: str) -> tuple[SessionState | None, TurnResult]:
        doc = session.document
        intent = parse_intent(user_text, doc.buckets)
        buckets_ui = buckets_for_ui(doc)

        if intent.kind == IntentKind.STOP:
            session.phase = NavPhase.DONE
            return None, TurnResult(
                speak_text="Stopped. Ask a new question anytime.",
                reply_full=doc.full_text,
                mode=NavPhase.DONE.value,
                session_id=None,
                buckets=buckets_ui,
                nav_hint="",
                layered=True,
            )

        if intent.kind == IntentKind.REPEAT:
            return session, TurnResult(
                speak_text=session.last_speak_text,
                reply_full=doc.full_text,
                mode=session.phase.value,
                session_id=session.session_id,
                buckets=buckets_ui,
                nav_hint=NAV_HINT,
                layered=True,
            )

        if intent.kind == IntentKind.READ_ALL:
            session.phase = NavPhase.DEEPEN
            session.bucket_index = 0
            session.item_index = 0
            parts = [read_all_intro(doc)]
            for item in doc.items[:3]:
                parts.append(item_text(item, partial=False))
            if len(doc.items) > 3:
                parts.append(
                    f"There are {len(doc.items) - 3} more on screen. Say next to continue reading."
                )
            speak = " ".join(parts)
            session.last_speak_text = speak
            return session, TurnResult(
                speak_text=speak,
                reply_full=doc.full_text,
                mode=NavPhase.DEEPEN.value,
                session_id=session.session_id,
                buckets=buckets_ui,
                nav_hint=NAV_HINT,
                layered=True,
            )

        if intent.kind == IntentKind.BACK:
            speak = orient_and_map_text(doc)
            session.phase = NavPhase.WAIT
            session.bucket_index = None
            session.item_index = 0
            session.last_speak_text = speak
            return session, TurnResult(
                speak_text=speak,
                reply_full=doc.full_text,
                mode=NavPhase.MAP.value,
                session_id=session.session_id,
                buckets=buckets_ui,
                nav_hint=NAV_HINT,
                layered=True,
            )

        if intent.kind == IntentKind.CHOOSE_BUCKET and intent.bucket_index is not None:
            return self._speak_bucket(session, intent.bucket_index, item_index=0)

        if intent.kind == IntentKind.NEXT:
            if session.bucket_index is None:
                return session, TurnResult(
                    speak_text="Pick a group first. " + NAV_HINT,
                    reply_full=doc.full_text,
                    mode=NavPhase.WAIT.value,
                    session_id=session.session_id,
                    buckets=buckets_ui,
                    nav_hint=NAV_HINT,
                    layered=True,
                )
            bucket = doc.buckets[session.bucket_index]
            next_idx = session.item_index + 1
            if next_idx >= len(bucket.items):
                return session, TurnResult(
                    speak_text="That's the last item in this group. Say back for the menu.",
                    reply_full=doc.full_text,
                    mode=NavPhase.WAIT.value,
                    session_id=session.session_id,
                    buckets=buckets_ui,
                    nav_hint=NAV_HINT,
                    layered=True,
                )
            return self._speak_bucket(session, session.bucket_index, item_index=next_idx)

        # Unrecognized in session — treat as new question signal for caller
        return None, TurnResult(
            speak_text="",
            reply_full=doc.full_text,
            mode="new_question",
            session_id=None,
            buckets=buckets_ui,
            nav_hint="",
            layered=True,
        )

    def _speak_bucket(
        self, session: SessionState, bucket_index: int, *, item_index: int
    ) -> tuple[SessionState, TurnResult]:
        doc = session.document
        if bucket_index < 0 or bucket_index >= len(doc.buckets):
            return session, TurnResult(
                speak_text="I didn't catch that group. " + NAV_HINT,
                reply_full=doc.full_text,
                mode=NavPhase.WAIT.value,
                session_id=session.session_id,
                buckets=buckets_for_ui(doc),
                nav_hint=NAV_HINT,
                layered=True,
            )

        bucket = doc.buckets[bucket_index]
        session.bucket_index = bucket_index
        session.item_index = item_index
        session.phase = NavPhase.DEEPEN

        if item_index == 0 and len(bucket.items) > 1:
            speak = bucket_summary(bucket, bucket_index + 1, len(doc.buckets))
        elif item_index < len(bucket.items):
            speak = item_text(bucket.items[item_index], partial=True)
        else:
            speak = "No more items in this group."

        session.last_speak_text = speak
        return session, TurnResult(
            speak_text=speak,
            reply_full=doc.full_text,
            mode=NavPhase.DEEPEN.value,
            session_id=session.session_id,
            buckets=buckets_for_ui(doc),
            nav_hint=NAV_HINT,
            layered=True,
        )
