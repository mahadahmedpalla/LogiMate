/**
 * AI Logisim Controller — Interactive Dashboard Application Logic
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const statusDot = document.getElementById("status-dot");
  const statusLabel = document.getElementById("status-label");
  const refreshStatusBtn = document.getElementById("refresh-status-btn");
  const btnLaunchLogisim = document.getElementById("btn-launch-logisim");
  const apiKeyBadge = document.getElementById("api-key-badge");
  const modelTagHeader = document.getElementById("model-tag-header");
  const activeModelPill = document.getElementById("active-model-pill");

  if (btnLaunchLogisim) {
    btnLaunchLogisim.addEventListener("click", async () => {
      btnLaunchLogisim.textContent = "Starting...";
      btnLaunchLogisim.disabled = true;
      try {
        const res = await fetch("/api/control/launch-logisim", { method: "POST" });
        const d = await res.json();
        if (!d.success) alert(d.message);
      } finally {
        setTimeout(() => {
          btnLaunchLogisim.textContent = "▶ Launch Logisim";
          btnLaunchLogisim.disabled = false;
          updateStatus();
        }, 1500);
      }
    });
  }

  // Controls
  const btnTick = document.getElementById("btn-tick");
  const btnClock = document.getElementById("btn-clock");
  const btnReset = document.getElementById("btn-reset");
  const btnLoadCirc = document.getElementById("btn-load-circ");

  // Chat
  const chatFeed = document.getElementById("chat-feed");
  const chatForm = document.getElementById("chat-form");
  const promptInput = document.getElementById("prompt-input");
  const sendBtn = document.getElementById("send-btn");
  const promptChips = document.querySelectorAll(".prompt-chip");

  // Pins & Circuit Info
  const pinsGrid = document.getElementById("pins-grid");
  const pinCountBadge = document.getElementById("pin-count-badge");
  const circuitPresencePill = document.getElementById("circuit-presence-pill");
  const xmlCodeView = document.getElementById("xml-code-view");
  const liveScreenshotImg = document.getElementById("live-screenshot-img");
  const screenshotPlaceholder = document.querySelector(".screenshot-placeholder");

  // Settings Modal
  const settingsModal = document.getElementById("settings-modal");
  const openSettingsBtn = document.getElementById("open-settings-btn");
  const closeSettingsBtn = document.getElementById("close-settings-btn");
  const cancelSettingsBtn = document.getElementById("cancel-settings-btn");
  const settingsForm = document.getElementById("settings-form");
  const cfgApiKey = document.getElementById("cfg-api-key");
  const cfgModelSelect = document.getElementById("cfg-model-select");
  const customModelGroup = document.getElementById("custom-model-group");
  const cfgCustomModel = document.getElementById("cfg-custom-model");
  const cfgThinkingBudget = document.getElementById("cfg-thinking-budget");
  const cfgOffsetX = document.getElementById("cfg-offset-x");
  const cfgOffsetY = document.getElementById("cfg-offset-y");
  const toggleKeyVis = document.getElementById("toggle-key-vis");
  const btnTestConnection = document.getElementById("btn-test-connection");
  const testResultBadge = document.getElementById("test-result-badge");

  let currentActivePins = {};

  // ----------------------------------------------------
  // Status Polling & Updates
  // ----------------------------------------------------

  async function updateStatus() {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) return;
      const data = await res.json();

      // Window status
      if (data.logisim && data.logisim.connected) {
        statusDot.className = "status-dot connected";
        statusLabel.textContent = `Connected: ${data.logisim.title || "Logisim 2.7.1"}`;
        statusLabel.title = `Window position: (${data.logisim.rect.left}, ${data.logisim.rect.top})`;
        if (btnLaunchLogisim) btnLaunchLogisim.classList.add("hidden");
      } else {
        statusDot.className = "status-dot searching";
        statusLabel.textContent = "Logisim not detected";
        statusLabel.title = "Click 'Launch Logisim' or open Logisim 2.7.1 on your desktop";
        if (btnLaunchLogisim) btnLaunchLogisim.classList.remove("hidden");
      }

      // API Key badge
      if (data.has_api_key) {
        apiKeyBadge.textContent = "Key Active";
        apiKeyBadge.className = "api-key-badge set";
      } else {
        apiKeyBadge.textContent = "Set Key";
        apiKeyBadge.className = "api-key-badge";
      }

      // Model display
      const modelDisplayName = getModelDisplayName(data.model_id);
      modelTagHeader.textContent = modelDisplayName;
      activeModelPill.textContent = modelDisplayName;

      // Circuit presence
      if (data.active_circuit) {
        circuitPresencePill.textContent = "Loaded (circuit.circ)";
        circuitPresencePill.className = "status-pill-small ready";
        updateSchematicView();
        updateXmlView();
      } else {
        circuitPresencePill.textContent = "No Circuit";
        circuitPresencePill.className = "status-pill-small";
      }

      // Render pins if changed
      if (data.active_pins && JSON.stringify(data.active_pins) !== JSON.stringify(currentActivePins)) {
        currentActivePins = data.active_pins;
        renderPins(currentActivePins);
      }
    } catch (err) {
      console.warn("Status poll error:", err);
    }
  }

  function getModelDisplayName(id) {
    if (!id) return "Gemini";
    if (id.includes("3.8")) return "Gemini 3.8 Flash";
    if (id.includes("3.7")) return "Gemini 3.7 Flash";
    if (id.includes("3.6")) return "Gemini 3.6 Flash";
    if (id.includes("2.5")) return "Gemini 2.5 Flash";
    if (id.includes("2.0")) return "Gemini 2.0 Flash";
    if (id.includes("1.5")) return "Gemini 1.5 Flash";
    return id;
  }

  // Poll every 3 seconds
  setInterval(updateStatus, 3000);
  updateStatus();
  refreshStatusBtn.addEventListener("click", updateStatus);

  // ----------------------------------------------------
  // Pins Board Rendering & Interactive Poke
  // ----------------------------------------------------

  function renderPins(pinMap) {
    pinsGrid.innerHTML = "";
    const pinNames = Object.keys(pinMap || {});
    pinCountBadge.textContent = `${pinNames.length} Pins`;

    if (pinNames.length === 0) {
      pinsGrid.innerHTML = '<div class="empty-pins-notice"><span>Generate a circuit to see interactive pins.</span></div>';
      return;
    }

    pinNames.forEach((pinName) => {
      const coord = pinMap[pinName];
      const pinEl = document.createElement("div");
      pinEl.className = "pin-chip";
      pinEl.innerHTML = `
        <div class="pin-header">
          <span class="pin-title">${escapeHtml(pinName)}</span>
          <span class="pin-coord">(${coord[0]}, ${coord[1]})</span>
        </div>
        <button class="pin-poke-btn" data-pin="${escapeHtml(pinName)}">POKE</button>
      `;

      pinEl.querySelector(".pin-poke-btn").addEventListener("click", async (e) => {
        const btn = e.currentTarget;
        btn.textContent = "POKING...";
        btn.disabled = true;

        try {
          const res = await fetch("/api/control/poke", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pin_name: pinName }),
          });
          const result = await res.json();
          if (result.success) {
            btn.textContent = "POKED!";
            setTimeout(() => {
              btn.textContent = "POKE";
              btn.disabled = false;
            }, 800);
          } else {
            alert(result.message || "Poke failed");
            btn.textContent = "POKE";
            btn.disabled = false;
          }
        } catch (err) {
          btn.textContent = "POKE";
          btn.disabled = false;
        }
      });

      pinsGrid.appendChild(pinEl);
    });
  }

  // ----------------------------------------------------
  // Quick Controls (Tick, Clock, Reset, Load)
  // ----------------------------------------------------

  btnTick.addEventListener("click", async () => {
    btnTick.disabled = true;
    try {
      const res = await fetch("/api/control/tick", { method: "POST" });
      const data = await res.json();
      if (!data.success) alert(data.message);
    } finally {
      setTimeout(() => (btnTick.disabled = false), 200);
    }
  });

  btnClock.addEventListener("click", async () => {
    btnClock.disabled = true;
    try {
      const res = await fetch("/api/control/toggle-clock", { method: "POST" });
      const data = await res.json();
      if (!data.success) alert(data.message);
    } finally {
      setTimeout(() => (btnClock.disabled = false), 200);
    }
  });

  btnReset.addEventListener("click", async () => {
    btnReset.disabled = true;
    try {
      const res = await fetch("/api/control/reset", { method: "POST" });
      const data = await res.json();
      if (!data.success) alert(data.message);
    } finally {
      setTimeout(() => (btnReset.disabled = false), 200);
    }
  });

  btnLoadCirc.addEventListener("click", async () => {
    btnLoadCirc.disabled = true;
    try {
      const res = await fetch("/api/control/load-circuit", { method: "POST" });
      const data = await res.json();
      alert(data.message);
    } finally {
      btnLoadCirc.disabled = false;
    }
  });

  // ----------------------------------------------------
  // Chat Conversation & Form
  // ----------------------------------------------------

  // Prompt chips
  promptChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      promptInput.value = chip.dataset.prompt;
      promptInput.focus();
    });
  });

  // Ctrl+Enter shortcut in textarea
  promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    // Append user message
    appendUserMessage(prompt);
    promptInput.value = "";
    sendBtn.disabled = true;

    // Show pending message
    const pendingId = appendPendingMessage();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      const data = await res.json();
      removeMessage(pendingId);

      if (!res.ok || !data.success) {
        appendAssistantMessage({
          thought: "",
          response: data.error || data.detail || "An error occurred while contacting the controller.",
          actions: [],
          isError: true,
        });
      } else {
        appendAssistantMessage({
          thought: data.thought,
          response: data.response,
          actions: data.executed_actions,
        });

        // If screenshot returned
        if (data.screenshot) {
          liveScreenshotImg.src = data.screenshot;
          liveScreenshotImg.classList.remove("hidden");
          if (screenshotPlaceholder) screenshotPlaceholder.classList.add("hidden");
        }

        // Update pins
        if (data.pin_map) {
          currentActivePins = data.pin_map;
          renderPins(data.pin_map);
        }

        // Update XML view and Live Canvas
        updateXmlView();
        updateSchematicView();
      }
    } catch (err) {
      removeMessage(pendingId);
      appendAssistantMessage({
        thought: "",
        response: `Network error: ${err.message}`,
        actions: [],
        isError: true,
      });
    } finally {
      sendBtn.disabled = false;
      updateStatus();
    }
  });

  async function updateSchematicView() {
    try {
      const res = await fetch("/api/circuit/diagram");
      if (!res.ok) return;
      const data = await res.json();
      if (data.exists) {
        renderSchematicSvg(data);
      }
    } catch (e) {
      console.warn("Schematic update error:", e);
    }
  }

  function renderSchematicSvg(data) {
    const svg = document.getElementById("schematic-svg");
    if (!svg) return;

    const comps = data.components || [];
    const wires = data.wires || [];

    if (comps.length === 0 && wires.length === 0) {
      svg.innerHTML = '<text x="250" y="140" fill="#64748b" text-anchor="middle" font-size="13" font-family="sans-serif">No components in circuit</text>';
      return;
    }

    // Calculate bounding box to dynamically scale SVG viewBox
    let minX = 9999, minY = 9999, maxX = -9999, maxY = -9999;
    comps.forEach(c => {
      minX = Math.min(minX, c.x - 60);
      maxX = Math.max(maxX, c.x + 60);
      minY = Math.min(minY, c.y - 40);
      maxY = Math.max(maxY, c.y + 40);
    });
    wires.forEach(w => {
      minX = Math.min(minX, w.from[0], w.to[0]);
      maxX = Math.max(maxX, w.from[0], w.to[0]);
      minY = Math.min(minY, w.from[1], w.to[1]);
      maxY = Math.max(maxY, w.from[1], w.to[1]);
    });

    const pad = 40;
    const width = Math.max(300, (maxX - minX) + pad * 2);
    const height = Math.max(200, (maxY - minY) + pad * 2);
    svg.setAttribute("viewBox", `${minX - pad} ${minY - pad} ${width} ${height}`);

    let elements = "";

    // 1. Render Wires (Electric cyan glow)
    wires.forEach(w => {
      elements += `<line x1="${w.from[0]}" y1="${w.from[1]}" x2="${w.to[0]}" y2="${w.to[1]}" stroke="#00e5ff" stroke-width="2.5" stroke-linecap="round" opacity="0.85"/>`;
    });

    // 2. Render Components
    comps.forEach(c => {
      const name = (c.name || "").toUpperCase();
      const x = c.x;
      const y = c.y;

      if (name === "PIN") {
        const isOutput = c.attrs && c.attrs.output === "true";
        const label = (c.attrs && c.attrs.label) || c.label || "";
        const width = parseInt((c.attrs && c.attrs.width) || "1", 10);
        const widthBadge = width > 1 ? ` <tspan fill="#38bdf8" font-size="9">[${width}b]</tspan>` : "";

        if (isOutput) {
          // Output Pin: Double circle probe or bus terminal
          elements += `
            <g class="comp-output">
              <circle cx="${x}" cy="${y}" r="12" fill="#080c14" stroke="#8b5cf6" stroke-width="2.5"/>
              <circle cx="${x}" cy="${y}" r="6" fill="#8b5cf6"/>
              <text x="${x + 18}" y="${y + 5}" fill="#c084fc" font-size="12" font-weight="700" font-family="'JetBrains Mono', monospace">${escapeHtml(label)}${widthBadge}</text>
            </g>
          `;
        } else {
          // Input Pin: Rectangular switch
          const valDisplay = width > 1 ? `0x0` : `0`;
          elements += `
            <g class="comp-input" style="cursor: pointer;">
              <rect x="${x - 16}" y="${y - 14}" width="32" height="28" rx="4" fill="#0e1422" stroke="#10b981" stroke-width="2.5"/>
              <text x="${x}" y="${y + 4}" fill="#34d399" font-size="10" font-weight="800" text-anchor="middle" font-family="'JetBrains Mono', monospace">${valDisplay}</text>
              <text x="${x - 22}" y="${y + 4}" fill="#6ee7b7" font-size="12" font-weight="700" text-anchor="end" font-family="'JetBrains Mono', monospace">${escapeHtml(label)}${widthBadge}</text>
            </g>
          `;
        }
      } else if (name === "SPLITTER") {
        // Splitter: Trunk and bus branches
        const incoming = parseInt((c.attrs && c.attrs.incoming) || "2", 10);
        const fanout = parseInt((c.attrs && c.attrs.fanout) || "2", 10);
        const appear = (c.attrs && c.attrs.appear) || "left";
        const facing = (c.attrs && c.attrs.facing) || "east";
        const dx = facing === "east" ? 20 : -20;
        
        let branchLines = "";
        for (let k = 0; k < fanout; k++) {
          const armY = appear === "left" ? y - (fanout - k) * 10 : y + (k + 1) * 10;
          branchLines += `
            <line x1="${x}" y1="${y}" x2="${x + dx}" y2="${armY}" stroke="#38bdf8" stroke-width="2" stroke-linecap="round"/>
            <circle cx="${x + dx}" cy="${armY}" r="3" fill="#38bdf8"/>
          `;
        }
        elements += `
          <g class="comp-splitter">
            <circle cx="${x}" cy="${y}" r="4" fill="#00e5ff"/>
            ${branchLines}
            <text x="${x + dx / 2}" y="${appear === 'left' ? y - fanout * 10 - 6 : y + fanout * 10 + 16}" fill="#38bdf8" font-size="10" font-weight="700" text-anchor="middle" font-family="'JetBrains Mono', monospace">SPLIT [/${incoming}b]</text>
          </g>
        `;
      } else if (name === "ADDER" || name.includes("ADDER")) {
        // Arithmetic Adder block
        const width = parseInt((c.attrs && c.attrs.width) || "8", 10);
        elements += `
          <g class="comp-arithmetic">
            <rect x="${x - 40}" y="${y - 25}" width="40" height="50" rx="4" fill="#1e1b4b" stroke="#6366f1" stroke-width="2"/>
            <text x="${x - 20}" y="${y + 6}" fill="#a5b4fc" font-size="18" font-weight="900" text-anchor="middle" font-family="'JetBrains Mono', monospace">+</text>
            <text x="${x - 20}" y="${y - 12}" fill="#818cf8" font-size="8" font-weight="700" text-anchor="middle" font-family="'JetBrains Mono', monospace">${width}-bit</text>
          </g>
        `;
      } else if (name === "MULTIPLEXER" || name === "MUX") {
        // Multiplexer trapezoid
        const width = parseInt((c.attrs && c.attrs.width) || "1", 10);
        elements += `
          <g class="comp-mux">
            <polygon points="${x - 40},${y - 30} ${x},${y - 18} ${x},${y + 18} ${x - 40},${y + 30}" fill="#1a1c2e" stroke="#ec4899" stroke-width="2"/>
            <text x="${x - 20}" y="${y + 4}" fill="#f472b6" font-size="10" font-weight="800" text-anchor="middle" font-family="'JetBrains Mono', monospace">MUX</text>
          </g>
        `;
      } else if (name === "REGISTER") {
        // Register memory block
        const width = parseInt((c.attrs && c.attrs.width) || "8", 10);
        elements += `
          <g class="comp-register">
            <rect x="${x - 40}" y="${y - 25}" width="40" height="50" rx="4" fill="#1e293b" stroke="#f59e0b" stroke-width="2"/>
            <text x="${x - 20}" y="${y - 6}" fill="#fbbf24" font-size="10" font-weight="800" text-anchor="middle" font-family="'JetBrains Mono', monospace">REG</text>
            <text x="${x - 20}" y="${y + 10}" fill="#fde68a" font-size="9" font-weight="600" text-anchor="middle" font-family="'JetBrains Mono', monospace">${width}b</text>
            <polygon points="${x - 25},${y + 25} ${x - 20},${y + 17} ${x - 15},${y + 25}" fill="none" stroke="#f59e0b" stroke-width="1.5"/>
          </g>
        `;
      } else if (name === "PROBE") {
        // Probe display readout
        elements += `
          <g class="comp-probe">
            <rect x="${x}" y="${y - 12}" width="50" height="24" rx="3" fill="#030712" stroke="#06b6d4" stroke-width="1.5"/>
            <text x="${x + 25}" y="${y + 4}" fill="#22d3ee" font-size="10" font-weight="700" text-anchor="middle" font-family="'JetBrains Mono', monospace">0x0000</text>
          </g>
        `;
      } else if (name.includes("AND")) {
        // AND Gate Symbol: flat back, rounded front (Output is at x, y)
        elements += `
          <g class="comp-gate">
            <path d="M ${x - 50} ${y - 25} L ${x - 25} ${y - 25} A 25 25 0 0 1 ${x} ${y} A 25 25 0 0 1 ${x - 25} ${y + 25} L ${x - 50} ${y + 25} Z" fill="#151d30" stroke="#38bdf8" stroke-width="2"/>
            <text x="${x - 30}" y="${y + 4}" fill="#94a3b8" font-size="10" font-weight="800" text-anchor="middle" font-family="'JetBrains Mono', monospace">AND</text>
          </g>
        `;
      } else if (name.includes("OR")) {
        // OR Gate Symbol: curved back, pointed front
        elements += `
          <g class="comp-gate">
            <path d="M ${x - 50} ${y - 25} Q ${x - 35} ${y} ${x - 50} ${y + 25} Q ${x - 15} ${y + 25} ${x} ${y} Q ${x - 15} ${y - 25} ${x - 50} ${y - 25} Z" fill="#151d30" stroke="#a855f7" stroke-width="2"/>
            <text x="${x - 28}" y="${y + 4}" fill="#cbd5e1" font-size="10" font-weight="800" text-anchor="middle" font-family="'JetBrains Mono', monospace">OR</text>
          </g>
        `;
      } else if (name.includes("NOT")) {
        // NOT Gate Symbol: triangle with inversion bubble
        elements += `
          <g class="comp-gate">
            <polygon points="${x - 30},${y - 15} ${x - 6},${y} ${x - 30},${y + 15}" fill="#151d30" stroke="#f43f5e" stroke-width="2"/>
            <circle cx="${x - 3}" cy="${y}" r="3" fill="#080c14" stroke="#f43f5e" stroke-width="1.5"/>
          </g>
        `;
      } else {
        // Generic chip block
        elements += `
          <g class="comp-generic">
            <rect x="${x - 50}" y="${y - 20}" width="50" height="40" rx="4" fill="#151d30" stroke="#e2e8f0" stroke-width="1.5"/>
            <text x="${x - 25}" y="${y + 4}" fill="#94a3b8" font-size="9" text-anchor="middle" font-family="'JetBrains Mono', monospace">${escapeHtml(name.replace("GATE", "").trim())}</text>
          </g>
        `;
      }
    });

    svg.innerHTML = elements;
  }

  async function updateXmlView() {
    try {
      const res = await fetch("/api/circuit/content");
      const data = await res.json();
      if (data.exists && data.xml) {
        xmlCodeView.textContent = data.xml;
      }
    } catch (e) {}
  }

  function appendUserMessage(text) {
    const card = document.createElement("div");
    card.className = "message-card user";
    card.innerHTML = `<div class="msg-body"><p>${escapeHtml(text)}</p></div>`;
    chatFeed.appendChild(card);
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }

  function appendPendingMessage() {
    const id = "pending-" + Date.now();
    const card = document.createElement("div");
    card.className = "message-card assistant";
    card.id = id;
    card.innerHTML = `
      <div class="msg-header">
        <div class="avatar-ring"><span class="avatar-text">AI</span></div>
        <div class="msg-meta">
          <span class="sender-name">AI Logisim Controller</span>
          <span class="msg-timestamp">Synthesizing & Executing...</span>
        </div>
      </div>
      <div class="msg-body">
        <p style="color: var(--accent-cyan);">Working with Logisim 2.7.1...</p>
      </div>
    `;
    chatFeed.appendChild(card);
    chatFeed.scrollTop = chatFeed.scrollHeight;
    return id;
  }

  function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function appendAssistantMessage({ thought, response, actions, isError = false }) {
    const card = document.createElement("div");
    card.className = "message-card assistant";

    let thoughtHtml = "";
    if (thought) {
      thoughtHtml = `
        <details class="thought-drawer">
          <summary>Reasoning Process</summary>
          <div class="thought-content">${escapeHtml(thought)}</div>
        </details>
      `;
    }

    let actionsHtml = "";
    if (actions && actions.length > 0) {
      const steps = actions
        .map((a) => {
          let icon = "✓";
          let statusClass = "success";
          if (a.status === "warning") {
            icon = "!";
            statusClass = "warning";
          } else if (a.status === "error") {
            icon = "✕";
            statusClass = "error";
          }
          return `<div class="timeline-step">
            <span class="step-icon ${statusClass}">${icon}</span>
            <span><strong>${escapeHtml(a.action)}:</strong> ${escapeHtml(a.details || a.status)}</span>
          </div>`;
        })
        .join("");

      actionsHtml = `
        <div class="actions-timeline">
          <span class="timeline-title">Executed Operations</span>
          ${steps}
        </div>
      `;
    }

    card.innerHTML = `
      <div class="msg-header">
        <div class="avatar-ring"><span class="avatar-text">AI</span></div>
        <div class="msg-meta">
          <span class="sender-name">AI Logisim Controller</span>
          <span class="msg-timestamp">Just now</span>
        </div>
      </div>
      <div class="msg-body" style="${isError ? "color: var(--accent-crimson);" : ""}">
        <p>${formatMarkdown(response)}</p>
        ${thoughtHtml}
        ${actionsHtml}
      </div>
    `;

    chatFeed.appendChild(card);
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }

  // ----------------------------------------------------
  // Settings Modal Handlers
  // ----------------------------------------------------

  async function loadSettings() {
    try {
      const res = await fetch("/api/settings");
      if (!res.ok) return;
      const data = await res.json();

      if (data.gemini_model === "custom" || !["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"].includes(data.gemini_model)) {
        cfgModelSelect.value = "custom";
        customModelGroup.classList.remove("hidden");
        cfgCustomModel.value = data.custom_model || data.gemini_model;
      } else {
        cfgModelSelect.value = data.gemini_model;
        customModelGroup.classList.add("hidden");
      }

      cfgOffsetX.value = data.canvas_offset_x || 200;
      cfgOffsetY.value = data.canvas_offset_y || 70;
      if (cfgThinkingBudget && data.thinking_budget !== undefined) {
        cfgThinkingBudget.value = String(data.thinking_budget);
      }
      if (data.gemini_api_key) {
        cfgApiKey.placeholder = `Configured (${data.gemini_api_key})`;
      }
    } catch (e) {
      console.warn("Failed to load settings:", e);
    }
  }

  openSettingsBtn.addEventListener("click", () => {
    loadSettings();
    settingsModal.classList.remove("hidden");
  });

  const closeModal = () => settingsModal.classList.add("hidden");
  closeSettingsBtn.addEventListener("click", closeModal);
  cancelSettingsBtn.addEventListener("click", closeModal);

  toggleKeyVis.addEventListener("click", () => {
    cfgApiKey.type = cfgApiKey.type === "password" ? "text" : "password";
  });

  cfgModelSelect.addEventListener("change", () => {
    if (cfgModelSelect.value === "custom") {
      customModelGroup.classList.remove("hidden");
      cfgCustomModel.focus();
    } else {
      customModelGroup.classList.add("hidden");
    }
  });

  btnTestConnection.addEventListener("click", async () => {
    testResultBadge.className = "test-result-badge";
    testResultBadge.textContent = "Testing...";
    testResultBadge.classList.remove("hidden");

    const key = cfgApiKey.value.trim();
    let model = cfgModelSelect.value;
    if (model === "custom") {
      model = cfgCustomModel.value.trim();
    }

    try {
      const res = await fetch("/api/test-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gemini_api_key: key,
          gemini_model: model,
          custom_model: cfgCustomModel.value.trim(),
        }),
      });
      const data = await res.json();
      if (data.success) {
        testResultBadge.className = "test-result-badge success";
        testResultBadge.textContent = data.message || "Connection Valid!";
      } else {
        testResultBadge.className = "test-result-badge error";
        testResultBadge.textContent = data.error || "Connection Failed";
      }
    } catch (e) {
      testResultBadge.className = "test-result-badge error";
      testResultBadge.textContent = e.message;
    }
  });

  settingsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      gemini_model: cfgModelSelect.value,
      custom_model: cfgCustomModel.value.trim(),
      thinking_budget: cfgThinkingBudget ? parseInt(cfgThinkingBudget.value, 10) : 1024,
      canvas_offset_x: parseInt(cfgOffsetX.value, 10) || 200,
      canvas_offset_y: parseInt(cfgOffsetY.value, 10) || 70,
    };
    if (cfgApiKey.value.trim()) {
      payload.gemini_api_key = cfgApiKey.value.trim();
    }

    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        closeModal();
        updateStatus();
      } else {
        alert(data.error || "Could not save settings.");
      }
    } catch (e) {
      alert("Error saving settings: " + e.message);
    }
  });

  // Utilities
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let formatted = escapeHtml(text);
    // Bold
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Code
    formatted = formatted.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Newlines
    formatted = formatted.replace(/\n/g, "<br>");
    return formatted;
  }

  // ----------------------------------------------------
  // Update Checker (GitHub Releases)
  // ----------------------------------------------------
  const updateModal = document.getElementById("update-modal");
  const closeUpdateBtn = document.getElementById("close-update-btn");
  const dismissUpdateBtn = document.getElementById("dismiss-update-btn");
  const btnOpenUpdateLink = document.getElementById("btn-open-update-link");
  const updateTagBadge = document.getElementById("update-tag-badge");
  const currentInstalledVer = document.getElementById("current-installed-ver");
  const updateNotesPreview = document.getElementById("update-notes-preview");

  function closeUpdateModal() {
    if (updateModal) updateModal.classList.add("hidden");
  }

  if (closeUpdateBtn) closeUpdateBtn.addEventListener("click", closeUpdateModal);
  if (dismissUpdateBtn) dismissUpdateBtn.addEventListener("click", closeUpdateModal);

  async function checkForUpdates() {
    try {
      const res = await fetch("/api/check-update");
      if (!res.ok) return;
      const d = await res.json();
      if (d.update_available) {
        if (updateTagBadge) updateTagBadge.textContent = "v" + d.latest_version + " Live";
        if (currentInstalledVer) currentInstalledVer.textContent = d.current_version;
        if (updateNotesPreview && d.release_notes) {
          updateNotesPreview.textContent = d.release_notes.substring(0, 350) + (d.release_notes.length > 350 ? "..." : "");
        }
        if (btnOpenUpdateLink) {
          btnOpenUpdateLink.onclick = () => {
            fetch("/api/open-external", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ url: d.html_url || "https://github.com/mahadahmedpalla/LogiMate/releases/latest" })
            });
          };
        }
        if (updateModal) updateModal.classList.remove("hidden");
      }
    } catch (e) {
      // Silently ignore if offline
    }
  }

  // Check on launch after a brief delay
  setTimeout(checkForUpdates, 1800);
});
