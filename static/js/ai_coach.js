/**
 * SpeakPro AI – AI Public Speaking Coach Chat Interface
 * Sends real-time queries to Gemini AI / NLP Coach engine and animates chat bubbles.
 */

document.addEventListener("DOMContentLoaded", function () {
  const chatForm = document.getElementById("coachChatForm");
  const chatInput = document.getElementById("coachChatInput");
  const chipButtons = document.querySelectorAll(".btn-prompt-chip");

  if (chatForm) {
    chatForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const text = chatInput.value.trim();
      if (text) {
        sendCoachMessage(text);
        chatInput.value = "";
      }
    });
  }

  chipButtons.forEach(btn => {
    btn.addEventListener("click", function () {
      const text = btn.getAttribute("data-prompt");
      if (text) {
        sendCoachMessage(text);
      }
    });
  });
});

async function sendCoachMessage(text) {
  const chatContainer = document.getElementById("coachChatMessages");
  if (!chatContainer) return;

  // 1. Append User bubble
  const userHtml = `
    <div class="chat-bubble-user animate__animated animate__fadeInRight">
      <div class="d-flex align-items-center gap-2 mb-1">
        <i class="bi bi-person-circle"></i>
        <small class="fw-bold">You</small>
      </div>
      <div>${escapeHtml(text)}</div>
    </div>
  `;
  chatContainer.insertAdjacentHTML("beforeend", userHtml);
  scrollToBottom(chatContainer);

  // 2. Append Typing Indicator
  const typingId = "typing_" + Date.now();
  const typingHtml = `
    <div id="${typingId}" class="chat-bubble-ai animate__animated animate__fadeInLeft">
      <div class="d-flex align-items-center gap-2 text-neon-green mb-1">
        <i class="bi bi-robot"></i>
        <small class="fw-bold">SpeakPro AI</small>
      </div>
      <div class="text-secondary">
        <span class="spinner-grow spinner-grow-sm me-1" role="status"></span>
        Thinking & coaching...
      </div>
    </div>
  `;
  chatContainer.insertAdjacentHTML("beforeend", typingHtml);
  scrollToBottom(chatContainer);

  // 3. Send request to backend
  try {
    const response = await fetch("/api/coach/chat/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken()
      },
      body: JSON.stringify({ message: text })
    });

    const data = await response.json();
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();

    const reply = (data.status === "success" && data.bot_response)
      ? data.bot_response
      : "I apologize, I am temporarily offline. Keep practicing your vocal variety and purposeful pauses!";

    const aiHtml = `
      <div class="chat-bubble-ai animate__animated animate__fadeInLeft">
        <div class="d-flex align-items-center gap-2 text-neon-green mb-1">
          <i class="bi bi-robot"></i>
          <small class="fw-bold">SpeakPro AI</small>
        </div>
        <div class="markdown-content">${formatMarkdownText(reply)}</div>
      </div>
    `;
    chatContainer.insertAdjacentHTML("beforeend", aiHtml);
    scrollToBottom(chatContainer);
  } catch (err) {
    console.error("Coach Chat Error:", err);
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();
    showToast("Error connecting to AI Coach.", "error");
  }
}

function scrollToBottom(container) {
  container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
  return text.replace(/[&<>"']/g, function (m) { return map[m]; });
}

function formatMarkdownText(text) {
  return text
    .replace(/\n\n/g, "<br><br>")
    .replace(/\n/g, "<br>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>");
}

function getCsrfToken() {
  const name = "csrftoken";
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue || "";
}
