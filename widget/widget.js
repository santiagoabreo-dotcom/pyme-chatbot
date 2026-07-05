/**
 * Pyme Chatbot - Widget embebible
 * ───────────────────────────────
 * Una sola línea de integración:
 *
 *   <script src="https://tu-dominio.com/widget/widget.js"
 *           data-client-id="cliente-1" defer></script>
 *
 * El widget solo conoce el client_id (público). La API key de
 * Anthropic vive únicamente en el backend y nunca se envía al
 * navegador ni aparece en este archivo.
 */
(function () {
  "use strict";

  function getConfig() {
    var script =
      document.currentScript ||
      (function () {
        var scripts = document.getElementsByTagName("script");
        return scripts[scripts.length - 1];
      })();

    var apiBase = script.getAttribute("data-api-base");
    if (!apiBase) {
      // Por defecto, asume que el backend sirve el widget desde /widget/widget.js
      // y que la API vive en el mismo origen.
      apiBase = script.src.replace(/\/widget\/widget\.js.*$/, "");
    }

    return {
      clientId: script.getAttribute("data-client-id"),
      apiBase: apiBase,
      title: script.getAttribute("data-title") || "¿En qué te ayudamos?",
      color: script.getAttribute("data-color") || "#0f766e",
    };
  }

  var cfg = getConfig();

  if (!cfg.clientId) {
    console.error("[PymeChatbot] Falta data-client-id en el <script> del widget.");
    return;
  }

  var style = document.createElement("style");
  style.textContent =
    ".fb-bubble{position:fixed;bottom:20px;right:20px;width:56px;height:56px;" +
    "border-radius:50%;background:" + cfg.color + ";color:#fff;display:flex;" +
    "align-items:center;justify-content:center;cursor:pointer;" +
    "box-shadow:0 4px 14px rgba(0,0,0,.25);z-index:2147483000;" +
    "font-family:system-ui,-apple-system,sans-serif;font-size:24px;border:none;}" +
    ".fb-window{position:fixed;bottom:88px;right:20px;width:320px;max-width:90vw;" +
    "height:420px;max-height:70vh;background:#fff;border-radius:12px;" +
    "box-shadow:0 8px 30px rgba(0,0,0,.3);display:none;flex-direction:column;" +
    "overflow:hidden;z-index:2147483000;font-family:system-ui,-apple-system,sans-serif;}" +
    ".fb-window.fb-open{display:flex;}" +
    ".fb-header{background:" + cfg.color + ";color:#fff;padding:12px 14px;" +
    "font-weight:600;font-size:14px;}" +
    ".fb-messages{flex:1;overflow-y:auto;padding:10px;font-size:13px;background:#fafafa;}" +
    ".fb-msg{margin-bottom:8px;padding:8px 10px;border-radius:8px;max-width:85%;" +
    "line-height:1.35;white-space:pre-wrap;word-break:break-word;}" +
    ".fb-msg.fb-user{background:#e2e8f0;margin-left:auto;}" +
    ".fb-msg.fb-bot{background:#ecfdf5;margin-right:auto;}" +
    ".fb-typing{font-size:12px;color:#94a3b8;padding:2px 10px 6px;}" +
    ".fb-input-row{display:flex;border-top:1px solid #e5e7eb;}" +
    ".fb-input{flex:1;border:none;padding:10px;font-size:13px;outline:none;}" +
    ".fb-send{border:none;background:" + cfg.color + ";color:#fff;padding:0 14px;cursor:pointer;}" +
    ".fb-send:disabled{opacity:.6;cursor:default;}";
  document.head.appendChild(style);

  var bubble = document.createElement("button");
  bubble.className = "fb-bubble";
  bubble.type = "button";
  bubble.setAttribute("aria-label", cfg.title);
  bubble.textContent = "💬";

  var win = document.createElement("div");
  win.className = "fb-window";
  win.innerHTML =
    '<div class="fb-header"></div>' +
    '<div class="fb-messages"></div>' +
    '<div class="fb-typing" style="display:none;">Escribiendo…</div>' +
    '<div class="fb-input-row">' +
    '<input class="fb-input" type="text" placeholder="Escribí tu mensaje..." />' +
    '<button class="fb-send" type="button">Enviar</button>' +
    "</div>";
  win.querySelector(".fb-header").textContent = cfg.title;

  document.body.appendChild(win);
  document.body.appendChild(bubble);

  var messagesEl = win.querySelector(".fb-messages");
  var inputEl = win.querySelector(".fb-input");
  var sendEl = win.querySelector(".fb-send");
  var typingEl = win.querySelector(".fb-typing");

  function addMessage(text, role) {
    var div = document.createElement("div");
    div.className = "fb-msg " + (role === "user" ? "fb-user" : "fb-bot");
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function setBusy(busy) {
    sendEl.disabled = busy;
    inputEl.disabled = busy;
    typingEl.style.display = busy ? "block" : "none";
  }

  function sendMessage() {
    var text = inputEl.value.trim();
    if (!text) return;

    addMessage(text, "user");
    inputEl.value = "";
    setBusy(true);

    fetch(cfg.apiBase + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_id: cfg.clientId, message: text }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) throw new Error(data.detail || "Error");
          return data;
        });
      })
      .then(function (data) {
        addMessage(data.response, "bot");
      })
      .catch(function () {
        addMessage("No pude responder en este momento. Probá de nuevo en un rato.", "bot");
      })
      .finally(function () {
        setBusy(false);
        inputEl.focus();
      });
  }

  bubble.addEventListener("click", function () {
    win.classList.toggle("fb-open");
    if (win.classList.contains("fb-open")) inputEl.focus();
  });

  sendEl.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter") sendMessage();
  });
})();
