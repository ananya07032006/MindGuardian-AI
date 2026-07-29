/**
 * MindGuardian AI — Chat Interface
 *
 * Handles:
 *  - Sending user messages via fetch() POST to /chat/send
 *  - Rendering user + bot bubbles dynamically
 *  - Auto-growing textarea
 *  - Typing indicator (dots animation)
 *  - Emotion / risk status display
 *  - Enter-to-send (Shift+Enter for newline)
 *  - Auto-scroll to latest message
 */

(function () {
  "use strict";

  /* ── DOM references ─────────────────────────────────────── */
  const messagesEl  = document.getElementById("chatMessages");
  const inputEl     = document.getElementById("userInput");
  const sendBtn     = document.getElementById("sendBtn");
  const typingEl    = document.getElementById("typingIndicator");
  const statusEl    = document.getElementById("emotionStatus");

  if (!messagesEl || !inputEl || !sendBtn) return;  // not on chat page

  /* ── Helpers ────────────────────────────────────────────── */

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function now() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** Convert simple Markdown links [text](url) → <a> tags */
  function renderLinks(text) {
    return escapeHtml(text).replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" class="text-brand fw-semibold" target="_blank" rel="noopener">$1</a>'
    );
  }

  /** Preserve newlines as <br> and render links */
  function formatBotText(text) {
    return renderLinks(text).replace(/\n/g, "<br>");
  }

  /* ── Emotion / risk badge helpers ──────────────────────── */

  const EMOTION_COLOR = {
    joy:      "success",
    sadness:  "primary",
    anger:    "danger",
    fear:     "warning",
    disgust:  "secondary",
    surprise: "info",
    neutral:  "light",
  };

  const RISK_COLOR = { low: "success", medium: "warning", high: "danger" };

  function emotionBadge(label) {
    if (!label || label === "neutral") return "";
    const cls = EMOTION_COLOR[label] || "secondary";
    return `<span class="badge bg-${cls} badge-sm">${label}</span>`;
  }

  function riskBadge(level) {
    if (!level || level === "low") return "";
    const cls = RISK_COLOR[level] || "secondary";
    return `<span class="badge bg-${cls} badge-sm ms-1">${level} risk</span>`;
  }

  /* ── Bubble renderers ───────────────────────────────────── */

  function appendUserBubble(text) {
    const wrap = document.createElement("div");
    wrap.className = "chat-bubble-wrap d-flex mb-3 justify-content-end";
    wrap.innerHTML = `
      <div class="chat-bubble bubble-user">
        <div class="bubble-text">${escapeHtml(text)}</div>
        <div class="bubble-time">${now()}</div>
      </div>`;
    messagesEl.insertBefore(wrap, typingEl);
    scrollToBottom();
    return wrap;
  }

  function appendBotBubble(text, emotion, riskLevel) {
    const metaHtml = emotionBadge(emotion) + riskBadge(riskLevel);
    const wrap = document.createElement("div");
    wrap.className = "chat-bubble-wrap d-flex mb-3 justify-content-start";
    wrap.innerHTML = `
      <div class="bot-avatar me-2 flex-shrink-0">
        <i data-feather="shield" style="width:18px;height:18px;color:var(--brand)"></i>
      </div>
      <div class="chat-bubble bubble-bot">
        <div class="bubble-text">${formatBotText(text)}</div>
        ${metaHtml ? `<div class="bubble-meta mt-1">${metaHtml}</div>` : ""}
        <div class="bubble-time">${now()}</div>
      </div>`;
    messagesEl.insertBefore(wrap, typingEl);
    feather.replace({ width: 18, height: 18 });
    scrollToBottom();
  }

  /* Remove "start conversation" empty state on first message */
  function clearEmptyState() {
    const empty = messagesEl.querySelector(".text-center.py-5");
    if (empty) empty.remove();
  }

  /* ── Typing indicator ───────────────────────────────────── */

  function showTyping() {
    typingEl.classList.remove("d-none");
    scrollToBottom();
  }

  function hideTyping() {
    typingEl.classList.add("d-none");
  }

  /* ── Status bar (emotion feedback) ─────────────────────── */

  function showStatus(emotion, emotionScore, riskLevel) {
    if (!emotion || emotion === "neutral") {
      statusEl.textContent = "";
      return;
    }
    const emojis = {
      joy:"😊", sadness:"😢", anger:"😠",
      fear:"😨", disgust:"🤢", surprise:"😲", neutral:"😐",
    };
    const emoji = emojis[emotion] || "🤔";
    const pct   = Math.round((emotionScore || 0) * 100);
    let msg = `${emoji} Detected emotion: <strong>${emotion}</strong> (${pct}% confidence)`;
    if (riskLevel === "high") {
      msg += ' &nbsp;|&nbsp; <span class="text-danger fw-semibold">⚠ High distress detected — please see the helplines link above.</span>';
    } else if (riskLevel === "medium") {
      msg += ' &nbsp;|&nbsp; <span class="text-warning fw-semibold">🔶 Elevated distress noted.</span>';
    }
    statusEl.innerHTML = msg;
  }

  /* ── Auto-grow textarea ─────────────────────────────────── */

  inputEl.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 140) + "px";
  });

  /* ── Send on Enter (Shift+Enter = newline) ──────────────── */

  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener("click", sendMessage);

  /* ── Core send function ─────────────────────────────────── */

  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;

    // Disable input while waiting
    inputEl.value = "";
    inputEl.style.height = "auto";
    inputEl.disabled = true;
    sendBtn.disabled = true;
    statusEl.textContent = "";

    clearEmptyState();
    appendUserBubble(text);
    showTyping();

    try {
      const resp = await fetch(SEND_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken":  CSRF_TOKEN,
        },
        body: JSON.stringify({ message: text }),
      });

      hideTyping();

      if (!resp.ok) {
        throw new Error(`Server error ${resp.status}`);
      }

      const data = await resp.json();

      appendBotBubble(data.reply, data.emotion, data.risk_level);
      showStatus(data.emotion, data.emotion_score, data.risk_level);

    } catch (err) {
      hideTyping();
      appendBotBubble(
        "I'm having trouble connecting right now. Please try again in a moment.",
        null, null
      );
      console.error("Chat error:", err);
    } finally {
      inputEl.disabled = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }

  /* ── Initial scroll ─────────────────────────────────────── */
  scrollToBottom();

})();
