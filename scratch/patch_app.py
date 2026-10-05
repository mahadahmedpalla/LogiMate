import re

with open("f:/original final downloads/logism ai control/ui/app.js", "r", encoding="utf-8") as f:
    js = f.read()

# Patch pin generation
pin_html = """      pinEl.className = "flex items-center justify-between p-3.5 rounded-lg bg-surface-container-low hover:bg-surface-container transition-colors";
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
      `;"""
js = re.sub(
    r'pinEl\.className = "pin-chip";\s*pinEl\.innerHTML = `[\s\S]*?`;',
    pin_html,
    js
)

# Patch appendUserMessage
user_msg = """  function appendUserMessage(text) {
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
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }"""
js = re.sub(
    r'function appendUserMessage\(text\) \{[\s\S]*?chatFeed\.scrollTop = chatFeed\.scrollHeight;\s*\}',
    user_msg,
    js
)

# Patch appendPendingMessage
pending_msg = """  function appendPendingMessage() {
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
    chatFeed.scrollTop = chatFeed.scrollHeight;
    return id;
  }"""
js = re.sub(
    r'function appendPendingMessage\(\) \{[\s\S]*?return id;\s*\}',
    pending_msg,
    js
)

# Patch appendAssistantMessage
assistant_msg = """  function appendAssistantMessage({ thought, response, actions, isError = false }) {
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
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }"""
js = re.sub(
    r'function appendAssistantMessage\(\{ thought, response, actions, isError = false \}\) \{[\s\S]*?chatFeed\.scrollTop = chatFeed\.scrollHeight;\s*\}',
    assistant_msg,
    js
)

with open("f:/original final downloads/logism ai control/ui/app.js", "w", encoding="utf-8") as f:
    f.write(js)

print("app.js patched successfully!")
