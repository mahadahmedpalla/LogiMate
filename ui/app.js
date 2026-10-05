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
      btnLaunchLogisim.innerHTML = '<span class="material-symbols-outlined text-[14px] animate-spin">refresh</span><span>Starting...</span>';
      btnLaunchLogisim.disabled = true;
      try {
        const res = await fetch("/api/control/launch-logisim", { method: "POST" });
        const d = await res.json();
        if (!d.success) alert(d.message);
      } finally {
        setTimeout(() => {
          btnLaunchLogisim.innerHTML = '<span class="material-symbols-outlined text-[14px]">play_arrow</span><span>Launch Logisim</span>';
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
  const saveSettingsBtn = document.getElementById("save-settings-btn");
  const btnResetChat = document.getElementById("btn-reset-chat");
  const settingsForm = document.getElementById("settings-form");
  const cfgProviderSelect = document.getElementById("cfg-provider-select");
  const geminiSettingsGroup = document.getElementById("gemini-settings-group");
  const groqSettingsGroup = document.getElementById("groq-settings-group");
  const cfgApiKey = document.getElementById("cfg-api-key");
  const cfgGroqKey = document.getElementById("cfg-groq-key");
  const cfgModelSelect = document.getElementById("cfg-model-select");
  const cfgGroqModelSelect = document.getElementById("cfg-groq-model-select");
  const customModelGroup = document.getElementById("custom-model-group");
  const cfgCustomModel = document.getElementById("cfg-custom-model");
  const cfgLogisimPath = document.getElementById("cfg-logisim-path");
  const cfgLogisimStatusHint = document.getElementById("cfg-logisim-status-hint");
  const cfgThinkingBudget = document.getElementById("cfg-thinking-budget");
  const cfgOffsetX = document.getElementById("cfg-offset-x");
  const cfgOffsetY = document.getElementById("cfg-offset-y");
  const toggleKeyVis = document.getElementById("toggle-key-vis");
  const toggleGroqKeyVis = document.getElementById("toggle-groq-key-vis");
  const btnTestConnection = document.getElementById("btn-test-connection");
  const testResultBadge = document.getElementById("test-result-badge");

  let currentActivePins = {};

  // ----------------------------------------------------
  // Status Polling & Updates
  // ----------------------------------------------------

  let statusPollInFlight = false;
  let lastCircuitVersion = null;

  async function updateStatus() {
    // Never stack requests if the previous poll is still running (slow PCs)
    if (statusPollInFlight) return;
    statusPollInFlight = true;
    try {
      const res = await fetch("/api/status");
      if (!res.ok) return;
      const data = await res.json();

      // Window status
      if (data.logisim && data.logisim.connected) {
        statusDot.className = "status-dot connected";
        const title = data.logisim.title || "Logisim 2.7.1";
        statusLabel.textContent = `Connected: ${title}`;
        statusLabel.className = "font-label-mono text-[12px] text-secondary font-semibold truncate";
        statusLabel.title = `Connected Window: "${title}"\nPosition: (${data.logisim.rect.left}, ${data.logisim.rect.top}) Size: ${data.logisim.rect.width}x${data.logisim.rect.height}`;
        if (btnLaunchLogisim) btnLaunchLogisim.classList.add("hidden");
      } else {
        statusDot.className = "status-dot searching";
        statusLabel.textContent = "Logisim not detected";
        statusLabel.className = "font-label-mono text-[12px] text-on-surface-variant font-medium truncate";
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

      // Model & Provider display
      const isGroq = (data.ai_provider || "gemini").toLowerCase() === "groq";
      const modelDisplayName = getModelDisplayName(data.model_id);
      const headerText = isGroq ? `Groq: ${modelDisplayName}` : modelDisplayName;
      modelTagHeader.textContent = headerText;
      activeModelPill.textContent = headerText;

      // Circuit presence
      if (data.active_circuit) {
        circuitPresencePill.textContent = "Loaded (circuit.circ)";
        circuitPresencePill.className = "status-pill-small ready";
        // Only re-fetch and redraw the canvas/XML when the circuit file actually changed
        const version = data.circuit_version !== undefined ? data.circuit_version : null;
        if (version === null || version !== lastCircuitVersion) {
          lastCircuitVersion = version;
          updateSchematicView();
          updateXmlView();
        }
      } else {
        circuitPresencePill.textContent = "No Circuit";
        circuitPresencePill.className = "status-pill-small";
        lastCircuitVersion = null;
      }

      // Render pins if changed
      if (data.active_pins && JSON.stringify(data.active_pins) !== JSON.stringify(currentActivePins)) {
        currentActivePins = data.active_pins;
        renderPins(currentActivePins);
      }
    } catch (err) {
      console.warn("Status poll error:", err);
    } finally {
      statusPollInFlight = false;
    }
  }

  function getModelDisplayName(id) {
    if (!id) return "AI Model";
    if (id.includes("qwen")) return "Qwen 3.8 27B";
    if (id.includes("llama-3.3-70b")) return "Llama 3.3 70B";
    if (id.includes("llama-3.1-8b")) return "Llama 3.1 8B";
    if (id.includes("deepseek-r1")) return "DeepSeek R1 70B";
    if (id.includes("deepseek")) return "DeepSeek";
    if (id.includes("3.8")) return "Gemini 3.8 Flash";
    if (id.includes("3.7")) return "Gemini 3.7 Flash";
    if (id.includes("3.6")) return "Gemini 3.6 Flash";
    if (id.includes("3.5")) return "Gemini 3.5 Flash";
    if (id.includes("3.1")) return "Gemini 3.1 Flash Lite";
    return id;
  }

  // Poll every 3 seconds (paused while the window is minimized/hidden to save CPU)
  setInterval(() => {
    if (!document.hidden) updateStatus();
  }, 3000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) updateStatus();
  });
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
      pinsGrid.innerHTML = '<div class="p-4 text-center bg-surface-container-low rounded-lg text-on-surface-variant text-[13px]"><span>Generate a circuit to see interactive pins.</span></div>';
      return;
    }

    pinNames.forEach((pinName) => {
      const coord = pinMap[pinName];
      const pinEl = document.createElement("div");
            pinEl.className = "flex items-center justify-between p-3.5 rounded-lg bg-surface-container-low hover:bg-surface-container transition-colors";
      pinEl.innerHTML = `
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-label-mono font-bold text-[12px]">
            ${escapeHtml(pinName.substring(0, 2).toUpperCase())}
          </div>
          <div>
            <div class="font-body-md text-[13px] font-medium text-on-surface">${escapeHtml(pinName)}</div>
            <div class="font-label-mono text-[10px] text-outline">(${coord[0]}, ${coord[1]})</div>
          </div>
        </div>
        <button class="pin-poke-btn px-3 py-1.5 rounded bg-surface-container hover:bg-surface-container-high transition-colors text-[11px] font-label-mono font-bold text-on-surface shadow-sm" data-pin="${escapeHtml(pinName)}">POKE</button>
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

    const deepModeCheckbox = document.getElementById("deep-mode-checkbox");
    const isDeepMode = deepModeCheckbox ? deepModeCheckbox.checked : false;

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
        body: JSON.stringify({ prompt, deep_mode: isDeepMode }),
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

  function saveMessageToHistory(msg) {
    try {
      const saved = sessionStorage.getItem("logimate_chat_history");
      const list = saved ? JSON.parse(saved) : [];
      list.push(msg);
      sessionStorage.setItem("logimate_chat_history", JSON.stringify(list));
    } catch (e) {
      console.warn("Could not save message:", e);
    }
  }

  function restoreChatHistory() {
    try {
      const saved = sessionStorage.getItem("logimate_chat_history");
      if (!saved) return;
      const msgs = JSON.parse(saved);
      if (!Array.isArray(msgs) || msgs.length === 0) return;
      msgs.forEach((m) => {
        if (m.type === "user") {
          appendUserMessage(m.text, false, false);
        } else if (m.type === "assistant") {
          appendAssistantMessage(m, false, false);
        }
      });
      // Scroll to bottom of chat feed once restored
      if (chatFeed && chatFeed.lastElementChild) {
        chatFeed.lastElementChild.scrollIntoView({ behavior: "auto", block: "end" });
      }
    } catch (e) {
      console.warn("Could not restore chat:", e);
    }
  }

  function appendUserMessage(text, save = true, scroll = true) {
    const card = document.createElement("div");
    card.className = "flex items-start justify-end gap-3 pl-8 mb-4";
    card.innerHTML = `
      <div class="rounded-xl rounded-tr-sm bg-primary-container text-on-primary-container p-4 shadow-sm max-w-lg">
        <div class="flex items-center gap-2 mb-1">
          <span class="font-label-mono text-[10px] opacity-80 uppercase">You</span>
          <span class="text-[9px] opacity-60">• Just now</span>
        </div>
        <p class="font-body-md text-[14px]">${escapeHtml(text)}</p>
      </div>
      <div class="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center font-label-mono text-[10px] font-medium text-on-surface shadow-sm flex-shrink-0">ME</div>
    `;
    chatFeed.appendChild(card);
    if (scroll) card.scrollIntoView({ behavior: "smooth", block: "end" });
    if (save) saveMessageToHistory({ type: "user", text });
  }

  function appendPendingMessage() {
    const id = "pending-" + Date.now();
    const card = document.createElement("div");
    card.className = "flex items-start gap-3 pr-4 mb-4";
    card.id = id;
    card.innerHTML = `
      <div class="w-8 h-8 rounded-full bg-surface-container flex items-center justify-center text-primary shadow-sm flex-shrink-0">
        <span class="material-symbols-outlined text-[18px]">smart_toy</span>
      </div>
      <div class="rounded-xl rounded-tl-sm bg-surface-container-lowest p-5 sm:p-6 shadow-sm flex-grow">
        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container-low text-on-surface-variant font-label-mono text-[11px] font-medium w-max">
          <span class="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
          <span>Synthesizing & Executing...</span>
        </div>
      </div>
    `;
    chatFeed.appendChild(card);
    card.scrollIntoView({ behavior: "smooth", block: "end" });
    return id;
  }

  function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function appendAssistantMessage({ thought, response, actions, isError = false }, save = true, scroll = true) {
    const card = document.createElement("div");
    card.className = "flex items-start gap-3 pr-4 mb-4";
    
    let thoughtHtml = "";
    if (thought) {
      thoughtHtml = `
        <details class="mt-3 border border-surface-container-high rounded p-2 text-[12px] bg-surface-container-low">
          <summary class="cursor-pointer font-label-mono text-outline font-medium select-none outline-none">Reasoning Process</summary>
          <div class="mt-2 text-on-surface-variant">${escapeHtml(thought)}</div>
        </details>
      `;
    }

    let actionsHtml = "";
    if (actions && actions.length > 0) {
      const steps = actions.map((a) => {
        const icon = a.status === "error" ? "error" : a.status === "warning" ? "warning" : "check_circle";
        const color = a.status === "error" ? "text-error" : a.status === "warning" ? "text-amber-500" : "text-secondary";
        return `
          <div class="flex items-center gap-2 py-1 border-t border-surface-container-high first:border-0">
            <span class="material-symbols-outlined text-[14px] ${color}">${icon}</span>
            <span class="font-body-md text-[13px] text-on-surface-variant">${escapeHtml(a.message)}</span>
          </div>
        `;
      }).join("");
      actionsHtml = `
        <div class="mt-3 p-3 rounded-lg bg-surface-container-lowest border border-surface-container flex flex-col gap-1">
          ${steps}
        </div>
      `;
    }

    const titleColor = isError ? "bg-error-container text-on-error-container" : "bg-secondary-fixed text-on-secondary-fixed-variant";
    const titleIcon = isError ? "error" : "check_circle";
    const titleText = isError ? "Error / Fallback" : "Task Completed";

    card.innerHTML = `
      <div class="w-8 h-8 rounded-full bg-surface-container flex items-center justify-center text-primary shadow-sm flex-shrink-0">
        <span class="material-symbols-outlined text-[18px]">smart_toy</span>
      </div>
      <div class="rounded-xl rounded-tl-sm bg-surface-container-lowest p-5 sm:p-6 shadow-sm flex-grow border ${isError ? 'border-error/30' : 'border-surface-container'}">
        <div class="flex items-center justify-between pb-2 mb-2">
          <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${titleColor} font-label-mono text-[11px] font-medium">
            <span class="material-symbols-outlined text-[14px]">${titleIcon}</span>
            <span>${titleText}</span>
          </div>
        </div>
        <div class="font-body-md text-[14px] text-on-surface leading-relaxed whitespace-pre-wrap">${escapeHtml(response)}</div>
        ${thoughtHtml}
        ${actionsHtml}
      </div>
    `;

    chatFeed.appendChild(card);
    if (scroll) card.scrollIntoView({ behavior: "smooth", block: "end" });
    if (save) saveMessageToHistory({ type: "assistant", thought, response, actions, isError });
  }

  // ----------------------------------------------------
  // Settings Modal Handlers
  // ----------------------------------------------------

  function updateCustomModelVisibility() {
    const provider = cfgProviderSelect ? cfgProviderSelect.value : "gemini";
    let isCustom = false;
    if (provider === "groq") {
      isCustom = cfgGroqModelSelect && cfgGroqModelSelect.value === "custom";
    } else {
      isCustom = cfgModelSelect && cfgModelSelect.value === "custom";
    }
    if (isCustom) {
      customModelGroup.classList.remove("hidden");
    } else {
      customModelGroup.classList.add("hidden");
    }
  }

  function toggleProviderUI(provider) {
    if (provider === "groq") {
      geminiSettingsGroup.classList.add("hidden");
      groqSettingsGroup.classList.remove("hidden");
    } else {
      geminiSettingsGroup.classList.remove("hidden");
      groqSettingsGroup.classList.add("hidden");
    }
    updateCustomModelVisibility();
  }

  if (cfgProviderSelect) {
    cfgProviderSelect.addEventListener("change", () => {
      toggleProviderUI(cfgProviderSelect.value);
    });
  }

  if (cfgModelSelect) {
    cfgModelSelect.addEventListener("change", () => {
      updateCustomModelVisibility();
      if (cfgModelSelect.value === "custom") cfgCustomModel.focus();
    });
  }

  if (cfgGroqModelSelect) {
    cfgGroqModelSelect.addEventListener("change", () => {
      updateCustomModelVisibility();
      if (cfgGroqModelSelect.value === "custom") cfgCustomModel.focus();
    });
  }

  if (toggleGroqKeyVis && cfgGroqKey) {
    toggleGroqKeyVis.addEventListener("click", () => {
      cfgGroqKey.type = cfgGroqKey.type === "password" ? "text" : "password";
      const icon = toggleGroqKeyVis.querySelector(".material-symbols-outlined");
      if (icon) icon.textContent = cfgGroqKey.type === "password" ? "visibility" : "visibility_off";
    });
  }

  async function loadSettings() {
    try {
      const res = await fetch("/api/settings");
      if (!res.ok) return;
      const data = await res.json();

      const provider = (data.ai_provider || "gemini").toLowerCase();
      if (cfgProviderSelect) cfgProviderSelect.value = provider;
      toggleProviderUI(provider);

      // Gemini Model selection
      if (data.gemini_model === "custom" || !["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"].includes(data.gemini_model)) {
        cfgModelSelect.value = "custom";
      } else {
        cfgModelSelect.value = data.gemini_model;
      }

      // Groq Model selection
      if (cfgGroqModelSelect) {
        if (data.groq_model === "custom" || !["qwen/qwen3.8-27b", "llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b", "llama-3.1-8b-instant"].includes(data.groq_model)) {
          cfgGroqModelSelect.value = "custom";
        } else {
          cfgGroqModelSelect.value = data.groq_model || "qwen/qwen3.8-27b";
        }
      }

      if (data.custom_model) {
        cfgCustomModel.value = data.custom_model;
      }
      updateCustomModelVisibility();

      if (cfgLogisimPath) {
        cfgLogisimPath.value = data.logisim_path || "";
        if (data.detected_logisim_path) {
          const isBundled = data.bundled_logisim ? " (Bundled 2.7.1 Active)" : "";
          cfgLogisimPath.placeholder = `${data.detected_logisim_path}${isBundled}`;
          if (cfgLogisimStatusHint) {
            cfgLogisimStatusHint.textContent = data.bundled_logisim
              ? `✅ Bundled Logisim 2.7.1 active at: ${data.detected_logisim_path}`
              : `🔍 Discovered Logisim at: ${data.detected_logisim_path}`;
            cfgLogisimStatusHint.style.color = "#34d399";
          }
        }
      }

      cfgOffsetX.value = data.canvas_offset_x || 200;
      cfgOffsetY.value = data.canvas_offset_y || 70;
      if (cfgThinkingBudget && data.thinking_budget !== undefined) {
        cfgThinkingBudget.value = String(data.thinking_budget);
      }
      if (data.gemini_api_key) {
        cfgApiKey.placeholder = `Configured (${data.gemini_api_key})`;
      }
      if (cfgGroqKey && data.groq_api_key) {
        cfgGroqKey.placeholder = `Configured (${data.groq_api_key})`;
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

  if (toggleKeyVis && cfgApiKey) {
    toggleKeyVis.addEventListener("click", () => {
      cfgApiKey.type = cfgApiKey.type === "password" ? "text" : "password";
      const icon = toggleKeyVis.querySelector(".material-symbols-outlined");
      if (icon) icon.textContent = cfgApiKey.type === "password" ? "visibility" : "visibility_off";
    });
  }

  if (btnTestConnection) {
    btnTestConnection.addEventListener("click", async () => {
      if (!testResultBadge) return;
      testResultBadge.className = "px-2.5 py-1 text-[11px] font-semibold rounded-full bg-surface-container-high text-on-surface-variant flex items-center gap-1.5 shadow-xs";
      testResultBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-primary animate-ping"></span><span>Testing API...</span>';
      testResultBadge.classList.remove("hidden");

      const provider = cfgProviderSelect ? cfgProviderSelect.value : "gemini";
      const payload = { ai_provider: provider };

      if (provider === "groq") {
        payload.groq_api_key = cfgGroqKey.value.trim();
        let model = cfgGroqModelSelect ? cfgGroqModelSelect.value : "qwen/qwen3.8-27b";
        if (model === "custom" && cfgCustomModel) {
          model = cfgCustomModel.value.trim();
        }
        payload.groq_model = model;
        if (cfgCustomModel) payload.custom_model = cfgCustomModel.value.trim();
      } else {
        payload.gemini_api_key = cfgApiKey.value.trim();
        let model = cfgModelSelect ? cfgModelSelect.value : "gemini-3.6-flash";
        if (model === "custom" && cfgCustomModel) {
          model = cfgCustomModel.value.trim();
        }
        payload.gemini_model = model;
        if (cfgCustomModel) payload.custom_model = cfgCustomModel.value.trim();
      }

      try {
        const res = await fetch("/api/test-key", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (data.success) {
          testResultBadge.className = "px-2.5 py-1 text-[11px] font-semibold rounded-full bg-secondary-container text-on-secondary-container flex items-center gap-1.5 shadow-xs";
          testResultBadge.innerHTML = `<span class="material-symbols-outlined text-[14px] text-secondary">check_circle</span><span>${escapeHtml(data.message || "Connection Valid!")}</span>`;
        } else {
          testResultBadge.className = "px-2.5 py-1 text-[11px] font-semibold rounded-full bg-error-container text-on-error-container flex items-center gap-1.5 shadow-xs";
          testResultBadge.innerHTML = `<span class="material-symbols-outlined text-[14px] text-error">error</span><span>${escapeHtml(data.error || "Connection Failed")}</span>`;
        }
      } catch (e) {
        testResultBadge.className = "px-2.5 py-1 text-[11px] font-semibold rounded-full bg-error-container text-on-error-container flex items-center gap-1.5 shadow-xs";
        testResultBadge.innerHTML = `<span class="material-symbols-outlined text-[14px] text-error">error</span><span>${escapeHtml(e.message)}</span>`;
      }
    });
  }

  const saveSettingsHandler = async (e) => {
    if (e) e.preventDefault();
    const provider = cfgProviderSelect ? cfgProviderSelect.value : "gemini";
    const payload = {
      ai_provider: provider,
      gemini_model: cfgModelSelect.value,
      groq_model: cfgGroqModelSelect ? cfgGroqModelSelect.value : "qwen/qwen3.8-27b",
      custom_model: cfgCustomModel.value.trim(),
      logisim_path: cfgLogisimPath ? cfgLogisimPath.value.trim() : "",
      thinking_budget: cfgThinkingBudget ? parseInt(cfgThinkingBudget.value, 10) : 1024,
      canvas_offset_x: parseInt(cfgOffsetX.value, 10) || 200,
      canvas_offset_y: parseInt(cfgOffsetY.value, 10) || 70,
    };
    if (cfgApiKey.value.trim()) {
      payload.gemini_api_key = cfgApiKey.value.trim();
    }
    if (cfgGroqKey && cfgGroqKey.value.trim()) {
      payload.groq_api_key = cfgGroqKey.value.trim();
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
  };

  if (settingsForm) settingsForm.addEventListener("submit", saveSettingsHandler);
  if (saveSettingsBtn) saveSettingsBtn.addEventListener("click", saveSettingsHandler);

  if (btnResetChat) {
    btnResetChat.addEventListener("click", async () => {
      btnResetChat.innerHTML = '<span class="material-symbols-outlined text-[13px] animate-spin">refresh</span><span>Resetting...</span>';
      try {
        await fetch("/api/chat/reset", { method: "POST" });
      } catch (err) {
        console.warn("Could not reset backend chat context:", err);
      }
      chatFeed.innerHTML = "";
      sessionStorage.removeItem("logimate_chat_history");
      setTimeout(() => {
        btnResetChat.innerHTML = '<span class="material-symbols-outlined text-[13px]">restart_alt</span><span>New Chat</span>';
      }, 350);

      const welcomeCard = document.getElementById("welcome-card");
      if (welcomeCard) welcomeCard.scrollIntoView({ behavior: "smooth", block: "start" });
      if (promptInput) promptInput.focus();
    });
  }

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

  // ----------------------------------------------------
  // Universal Zoom Controller (Ctrl +, Ctrl -, Ctrl 0, Ctrl + Wheel)
  // ----------------------------------------------------
  let currentZoom = parseFloat(localStorage.getItem("logimate_ui_zoom")) || 1.0;
  if (currentZoom < 0.5 || currentZoom > 2.0 || isNaN(currentZoom)) currentZoom = 1.0;

  function applyZoom(zoom) {
    currentZoom = Math.round(zoom * 100) / 100;
    currentZoom = Math.max(0.5, Math.min(2.0, currentZoom));
    document.body.style.zoom = currentZoom;
    try {
      localStorage.setItem("logimate_ui_zoom", currentZoom.toString());
    } catch (e) {}
  }

  // Restore saved zoom if customized
  if (currentZoom !== 1.0) {
    applyZoom(currentZoom);
  }

  // Hotkey listener for Ctrl/Cmd +, -, 0
  window.addEventListener("keydown", (e) => {
    if (!e.ctrlKey && !e.metaKey) return;

    if (e.key === "+" || e.key === "=" || e.key === "Add") {
      e.preventDefault();
      applyZoom(currentZoom + 0.1);
    } else if (e.key === "-" || e.key === "_" || e.key === "Subtract") {
      e.preventDefault();
      applyZoom(currentZoom - 0.1);
    } else if (e.key === "0" || e.key === "Numpad0") {
      e.preventDefault();
      applyZoom(1.0);
    }
  });

  // Mouse wheel listener with Ctrl/Cmd
  window.addEventListener(
    "wheel",
    (e) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        if (e.deltaY < 0) {
          applyZoom(currentZoom + 0.05);
        } else if (e.deltaY > 0) {
          applyZoom(currentZoom - 0.05);
        }
      }
    },
    { passive: false }
  );

  // Restore chat messages from session storage
  restoreChatHistory();

  // Check on launch after a brief delay
  setTimeout(checkForUpdates, 1800);
});
