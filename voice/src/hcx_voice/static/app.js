(() => {
  const statusEl = document.getElementById("status");
  const ptt = document.getElementById("ptt");
  const youEl = document.getElementById("you");
  const hermesEl = document.getElementById("hermes");
  const player = document.getElementById("player");

  let mediaRecorder = null;
  let chunks = [];
  let holding = false;
  let busy = false;

  function setStatus(text, cls) {
    statusEl.textContent = text;
    statusEl.className = "status" + (cls ? " " + cls : "");
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
      mediaRecorder.start(100);
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
      if (recorder.state !== "inactive") recorder.stop();
      else {
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

  async function sendTurn(blob) {
    busy = true;
    setStatus("thinking", "thinking");
    youEl.textContent = "…";
    hermesEl.textContent = "…";
    try {
      const fd = new FormData();
      const ext = blob.type.includes("mp4") ? "m4a" : "webm";
      fd.append("audio", blob, "utterance." + ext);
      const res = await fetch("/turn", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail || res.statusText || "request failed";
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      youEl.textContent = data.transcript || "—";
      hermesEl.textContent = data.reply || "—";
      if (data.audio_base64) {
        const mime = data.content_type || "audio/wav";
        player.src = "data:" + mime + ";base64," + data.audio_base64;
        setStatus("speaking", "speaking");
        try {
          await player.play();
        } catch (_) {
          /* user gesture may be required on some browsers after async */
        }
        player.onended = () => setStatus("idle");
      } else {
        setStatus("idle");
      }
    } catch (err) {
      setStatus("error: " + (err.message || err), "error");
      hermesEl.textContent = "—";
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

  // Prevent context menu on long-press (mobile)
  ptt.addEventListener("contextmenu", (e) => e.preventDefault());
})();
