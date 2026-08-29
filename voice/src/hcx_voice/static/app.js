(() => {
  const statusEl = document.getElementById("status");
  const ptt = document.getElementById("ptt");
  const youEl = document.getElementById("you");
  const hermesEl = document.getElementById("hermes");
  const navHintEl = document.getElementById("nav-hint");
  const bucketsEl = document.getElementById("buckets");
  const player = document.getElementById("player");

  const SESSION_KEY = "hcx_voice_session_id";
  let sessionId = localStorage.getItem(SESSION_KEY) || null;

  let mediaRecorder = null;
  let chunks = [];
  let holding = false;
  let busy = false;

  function setStatus(text, cls) {
    statusEl.textContent = text;
    statusEl.className = "status" + (cls ? " " + cls : "");
  }

  function setSessionId(id) {
    sessionId = id || null;
    if (sessionId) localStorage.setItem(SESSION_KEY, sessionId);
    else localStorage.removeItem(SESSION_KEY);
  }

  function renderBuckets(buckets) {
    bucketsEl.innerHTML = "";
    if (!buckets || !buckets.length) return;
    buckets.forEach((b, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "bucket-chip";
      btn.textContent = (b.label || "group") + (b.count ? " (" + b.count + ")" : "");
      btn.addEventListener("click", () => sendNav(String(idx + 1)));
      bucketsEl.appendChild(btn);
    });
  }

  function pickMime() {
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/ogg;codecs=opus",
    ];
    for (const t of candidates) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported(t)) return t;
    }
    return "";
  }

  async function startRecording() {
    if (busy || holding) return;
    holding = true;
    ptt.setAttribute("aria-pressed", "true");
    chunks = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = pickMime();
      mediaRecorder = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.push(e.data);
      };
      mediaRecorder.start();
      setStatus("recording", "recording");
    } catch (err) {
      holding = false;
      ptt.setAttribute("aria-pressed", "false");
      setStatus("mic error: " + (err.message || err), "error");
    }
  }

  async function stopRecording() {
    if (!holding || !mediaRecorder) {
      holding = false;
      ptt.setAttribute("aria-pressed", "false");
      return;
    }
    holding = false;
    ptt.setAttribute("aria-pressed", "false");

    const recorder = mediaRecorder;
    mediaRecorder = null;
    const blob = await new Promise((resolve) => {
      recorder.onstop = () => {
        const type = recorder.mimeType || "audio/webm";
        resolve(new Blob(chunks, { type }));
        recorder.stream.getTracks().forEach((t) => t.stop());
      };
      if (recorder.state !== "inactive") {
        try {
          recorder.requestData();
        } catch (_) {}
        recorder.stop();
      } else {
        recorder.stream.getTracks().forEach((t) => t.stop());
        resolve(new Blob(chunks, { type: "audio/webm" }));
      }
    });

    if (!blob.size) {
      setStatus("no audio captured", "error");
      return;
    }
    await sendTurn(blob);
  }

  async function applyTurnResponse(data) {
    youEl.textContent = data.transcript || "—";
    hermesEl.textContent = data.reply || "—";
    navHintEl.textContent = data.nav_hint || "";
    renderBuckets(data.buckets);
    setSessionId(data.session_id || null);

    if (data.audio_base64) {
      const mime = data.content_type || "audio/wav";
      player.src = "data:" + mime + ";base64," + data.audio_base64;
      setStatus("speaking (" + (data.mode || "reply") + ")", "speaking");
      try {
        await player.play();
      } catch (_) {}
      player.onended = () => setStatus("idle");
    } else {
      setStatus("idle");
    }
  }

  async function sendTurn(blob) {
    busy = true;
    setStatus("thinking", "thinking");
    youEl.textContent = "…";
    hermesEl.textContent = "…";
    try {
      const fd = new FormData();
      const ext = blob.type.includes("mp4") ? "m4a" : "webm";
      fd.append("audio", blob, "utterance." + ext);
      const headers = {};
      if (sessionId) headers["X-Session-Id"] = sessionId;
      const res = await fetch("/turn", { method: "POST", body: fd, headers });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || res.statusText || "request failed";
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      await applyTurnResponse(data);
    } catch (err) {
      setStatus("error: " + (err.message || err), "error");
      hermesEl.textContent = "—";
    } finally {
      busy = false;
    }
  }

  async function sendNav(command) {
    if (!sessionId || busy) return;
    busy = true;
    setStatus("navigating", "thinking");
    try {
      const res = await fetch("/nav", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, command }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || res.statusText || "nav failed";
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      await applyTurnResponse(data);
    } catch (err) {
      setStatus("error: " + (err.message || err), "error");
    } finally {
      busy = false;
    }
  }

  function onDown(e) {
    e.preventDefault();
    if (e.pointerType === "mouse" && e.button !== 0) return;
    try {
      ptt.setPointerCapture(e.pointerId);
    } catch (_) {}
    startRecording();
  }

  function onUp(e) {
    e.preventDefault();
    stopRecording();
  }

  ptt.addEventListener("pointerdown", onDown);
  ptt.addEventListener("pointerup", onUp);
  ptt.addEventListener("pointercancel", onUp);
  ptt.addEventListener("lostpointercapture", () => {
    if (holding) stopRecording();
  });
  ptt.addEventListener("contextmenu", (e) => e.preventDefault());
})();
