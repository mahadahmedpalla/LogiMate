import json

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
  <title>LogiMate — AI Logisim Controller</title>
  <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet"/>
  <link href="https://fonts.googleapis.com" rel="preconnect"/>
  <link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet"/>
  <link rel="icon" type="image/png" href="/static/favicon.png">
  <style>
    @layer base{html,body{margin:0;padding:0;}body{overscroll-behavior:none;}main>:first-child{margin-top:0!important;}main>:last-child{margin-bottom:0!important;}}
    ::-webkit-scrollbar{display:none;}
    
    /* Preserve some essential overrides from old style.css */
    .hidden { display: none !important; }
    svg text { user-select: none; }
    .status-dot { transition: background-color 0.3s; }
    .status-dot.searching { background-color: #facc15; }
    .status-dot.connected { background-color: #10b981; }
    .status-dot.error { background-color: #ef4444; }
  </style>
  <script src="https://cdn.tailwindcss.com"></script>
  <script id="tailwind-config">
    tailwind.config={"darkMode":"class","theme":{"extend":{"colors":{"on-tertiary-fixed":"#0f0069","on-secondary-container":"#00714e","surface-container-low":"#f1f3ff","inverse-primary":"#c3c0ff","primary-fixed-dim":"#c3c0ff","on-secondary":"#ffffff","primary-container":"#4338ca","inverse-surface":"#293040","error":"#ba1a1a","on-surface-variant":"#464554","secondary-fixed":"#85f8c4","on-primary":"#ffffff","error-container":"#ffdad6","surface-variant":"#dce2f7","surface-dim":"#d3daef","on-secondary-fixed-variant":"#005137","inverse-on-surface":"#edf0ff","tertiary-fixed":"#e2dfff","on-primary-fixed":"#100069","on-error-container":"#93000a","primary":"#2a14b4","on-secondary-fixed":"#002114","surface-bright":"#f9f9ff","on-background":"#141b2b","tertiary-container":"#3f33d6","on-tertiary-container":"#c1beff","background":"#f9f9ff","surface-tint":"#5148d7","on-tertiary":"#ffffff","surface-container":"#e9edff","on-primary-fixed-variant":"#372abf","surface-container-high":"#e1e8fd","on-tertiary-fixed-variant":"#3323cc","primary-fixed":"#e3dfff","surface-container-highest":"#dce2f7","on-error":"#ffffff","surface-container-lowest":"#ffffff","tertiary-fixed-dim":"#c3c0ff","outline":"#777586","secondary":"#006c4a","secondary-container":"#82f5c1","outline-variant":"#c7c4d7","on-primary-container":"#c1beff","tertiary":"#2402c1","secondary-fixed-dim":"#68dba9","surface":"#f9f9ff","on-surface":"#141b2b"},"borderRadius":{"DEFAULT":"0.125rem","lg":"0.25rem","xl":"0.5rem","full":"0.75rem"},"fontFamily":{"headline-lg":["Space Grotesk"],"body-md":["Inter"],"label-mono":["JetBrains Mono"],"headline-md":["Space Grotesk"],"display-hero":["Space Grotesk"],"body-lg":["Inter"],"code-sm":["JetBrains Mono"],"headline-sm":["Space Grotesk"],"body-sm":["Inter"],"display-hero-mobile":["Space Grotesk"],"code-md":["JetBrains Mono"]}}}}
  </script>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body class="bg-surface font-body-md text-on-surface antialiased">
  <header class="fixed top-0 left-0 right-0 z-50 bg-surface/85 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
    <div class="h-16 w-full px-6 flex items-center justify-between gap-4">
      <div class="flex items-center gap-5">
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full bg-error/70 inline-block"></span>
          <span class="w-3 h-3 rounded-full bg-amber-400/80 inline-block"></span>
          <span class="w-3 h-3 rounded-full bg-secondary-container inline-block"></span>
        </div>
        <div class="flex items-center gap-2.5 pl-2">
          <div class="w-7 h-7 rounded-xl bg-surface-container flex items-center justify-center text-primary shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
            <span class="material-symbols-outlined text-[18px]">smart_toy</span>
          </div>
          <span class="font-headline-sm text-headline-sm text-on-surface tracking-tight font-semibold">LogiMate v1.6</span>
        </div>
        <div id="window-status-badge" class="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container-low">
          <span id="status-dot" class="w-2 h-2 rounded-full bg-secondary animate-pulse searching"></span>
          <span id="status-label" class="font-label-mono text-label-mono text-secondary font-medium tracking-wide">Detecting Logisim 2.7.1...</span>
        </div>
      </div>
      
      <div class="flex items-center gap-3">
        <button id="btn-launch-logisim" class="hidden flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-surface-container-lowest hover:bg-surface-container-high transition-colors shadow-[0_1px_2px_rgba(0,0,0,0.04)] group" type="button">
          <span class="material-symbols-outlined text-secondary text-[17px]">play_arrow</span>
          <span class="font-body-md text-body-md text-on-surface font-medium">Launch Logisim</span>
        </button>
        
        <button id="open-settings-btn" class="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-surface-container-low hover:bg-surface-container transition-colors text-on-surface-variant hover:text-on-surface">
          <span class="material-symbols-outlined text-[19px]">settings</span>
          <span id="model-tag-header" class="font-label-mono text-[12px]">Gemini</span>
          <span id="api-key-badge" class="px-1.5 py-0.5 bg-error/10 text-error rounded text-[10px] uppercase font-bold">Set Key</span>
        </button>
      </div>
    </div>
  </header>

  <main class="w-full pt-16 bg-surface min-h-[calc(100vh-4rem)]">
    <div class="flex flex-col w-full">
      <div class="w-full max-w-7xl mx-auto px-6 lg:px-10 py-8 flex flex-col gap-8">
        
        <div class="flex flex-wrap items-center justify-between gap-4 pb-2">
          <div class="flex items-center gap-3">
            <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-container-lowest shadow-sm">
              <span class="w-2.5 h-2.5 rounded-full bg-secondary animate-pulse"></span>
              <span class="font-body-sm text-body-sm font-medium text-on-surface">Logisim Desktop Controlled</span>
              <span class="font-label-mono text-label-mono text-outline">IPC Engine</span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button id="refresh-status-btn" class="px-3.5 py-1.5 rounded-full bg-surface-container-lowest hover:bg-surface-container-high transition-colors font-body-sm text-body-sm font-medium text-on-surface shadow-sm flex items-center gap-1.5" type="button">
              <span class="material-symbols-outlined text-[16px] text-primary">refresh</span>
              <span>Refresh IPC</span>
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <!-- LEFT COLUMN: AI Conversation -->
          <div class="lg:col-span-7 flex flex-col gap-6">
            
            <div class="relative overflow-hidden rounded-xl bg-surface-container-lowest p-6 sm:p-8 shadow-sm">
              <div class="flex flex-col sm:flex-row items-center sm:items-start gap-6">
                <div class="relative flex-shrink-0 w-28 h-28 sm:w-32 sm:h-32 rounded-xl bg-surface-container-low flex items-center justify-center overflow-hidden shadow-inner">
                  <div class="w-full h-full flex items-center justify-center bg-primary/10">
                    <span class="material-symbols-outlined text-6xl text-primary">smart_toy</span>
                  </div>
                  <div class="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-secondary flex items-center justify-center text-on-secondary shadow-sm">
                    <span class="material-symbols-outlined text-[14px]">bolt</span>
                  </div>
                </div>
                <div class="flex flex-col text-center sm:text-left flex-grow">
                  <div class="inline-flex items-center self-center sm:self-start gap-1.5 px-2.5 py-0.5 rounded-full bg-primary-fixed text-on-primary-fixed font-label-mono text-label-mono mb-2">
                    <span>CIRCUIT COPILOT</span>
                  </div>
                  <h2 class="font-headline-lg text-headline-lg text-on-surface tracking-tight">
                    Hi! What would you like to build today?
                  </h2>
                  <p class="font-body-md text-body-md text-on-surface-variant mt-2 max-w-xl">
                    Tell me in plain English, and I’ll place every gate, connect the wires, and show you how it works step-by-step.
                  </p>
                </div>
              </div>
              
              <div class="mt-6 pt-5 bg-surface-container-low/60 rounded-xl p-4">
                <span class="font-label-mono text-label-mono uppercase tracking-wider text-outline block mb-3">Popular Beginner Ideas:</span>
                <div class="flex flex-wrap gap-2">
                  <button class="prompt-chip group px-3 py-1.5 rounded-full bg-surface-container-lowest hover:bg-primary-container hover:text-on-primary-container transition-all font-body-sm text-body-sm font-medium text-on-surface shadow-sm flex items-center gap-1.5" data-prompt="Build a 1-bit Full Adder with inputs A, B, Cin">
                    <span>💡</span><span>Full Adder</span>
                  </button>
                  <button class="prompt-chip group px-3 py-1.5 rounded-full bg-surface-container-lowest hover:bg-primary-container hover:text-on-primary-container transition-all font-body-sm text-body-sm font-medium text-on-surface shadow-sm flex items-center gap-1.5" data-prompt="Create a 2-to-1 Multiplexer">
                    <span>🔢</span><span>2:1 Mux</span>
                  </button>
                  <button class="prompt-chip group px-3 py-1.5 rounded-full bg-surface-container-lowest hover:bg-primary-container hover:text-on-primary-container transition-all font-body-sm text-body-sm font-medium text-on-surface shadow-sm flex items-center gap-1.5" data-prompt="Build an SR Latch using NOR gates">
                    <span>🚪</span><span>SR Latch</span>
                  </button>
                </div>
              </div>
            </div>

            <!-- Chat & Request Thread -->
            <div id="chat-feed" class="flex flex-col gap-4">
              <!-- Will be populated by app.js -->
            </div>

            <!-- Clean Floating Prompt Bar -->
            <div class="sticky bottom-6 z-20 w-full mt-2">
              <form id="chat-form" class="p-2 rounded-xl bg-surface-container-lowest shadow-xl border border-surface-container-high">
                <div class="flex items-center gap-2">
                  <input id="prompt-input" class="flex-grow bg-transparent px-3 py-2 font-body-md text-body-md text-on-surface placeholder:text-outline focus:outline-none" placeholder="Describe what you want to build in plain English..." type="text"/>
                  <button id="send-btn" type="submit" class="px-4 py-2 rounded-full bg-primary-container hover:bg-primary transition-all text-on-primary font-body-md text-body-md font-medium shadow-sm flex items-center gap-1.5 flex-shrink-0">
                    <span>Build Circuit</span>
                    <span class="material-symbols-outlined text-[16px]">arrow_forward</span>
                  </button>
                </div>
                <div class="px-3 pt-2 pb-1 flex items-center justify-between text-outline font-label-mono text-[11px]">
                  <span class="flex items-center gap-3">
                    <label class="flex items-center gap-1.5 cursor-pointer hover:text-primary transition-colors">
                      <input type="checkbox" id="deep-mode-checkbox" class="accent-primary w-3 h-3">
                      <span class="font-medium text-primary">Deep Mode (Auto-Repair)</span>
                    </label>
                    <span id="active-model-pill" class="bg-surface-container-high px-1.5 py-0.5 rounded text-on-surface-variant">Gemini</span>
                  </span>
                  <span class="hidden sm:inline flex items-center gap-1">
                    <span class="material-symbols-outlined text-[13px]">keyboard_return</span>
                    <span>Press Return to build automatically</span>
                  </span>
                </div>
              </form>
            </div>
          </div>

          <!-- RIGHT COLUMN: Visual Circuit & Interactive Controls -->
          <div class="lg:col-span-5 flex flex-col gap-6">
            
            <div id="schematic-card" class="rounded-xl bg-surface-container-lowest p-5 sm:p-6 shadow-sm border border-surface-container-high">
              <div class="flex items-center justify-between pb-4">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-primary text-[20px]">account_tree</span>
                  <span class="font-headline-sm text-headline-sm text-on-surface">Live Circuit Canvas</span>
                </div>
                <div class="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-surface-container text-secondary font-label-mono text-label-mono">
                  <span id="circuit-presence-pill" class="font-semibold text-[10px] tracking-wider uppercase">No Circuit</span>
                </div>
              </div>
              
              <div id="schematic-viewport" class="relative w-full rounded-xl bg-surface-container-low p-6 overflow-hidden border border-surface-container flex items-center justify-center min-h-[200px]">
                <svg id="schematic-svg" class="w-full h-auto text-on-surface" viewBox="0 0 500 280">
                  <text x="250" y="140" fill="#64748b" text-anchor="middle" font-size="13" font-family="sans-serif">Ask AI to build a circuit to render canvas</text>
                </svg>
              </div>
              
              <div class="flex items-center justify-between mt-4">
                <button id="btn-load-circ" class="inline-flex items-center gap-1 font-body-sm text-body-sm font-medium text-primary hover:underline bg-transparent">
                  <span class="material-symbols-outlined text-[15px]">open_in_new</span>
                  <span>Load in Logisim</span>
                </button>
                <a id="btn-download-circ" href="/api/circuit/download" download="circuit.circ" class="inline-flex items-center gap-1 font-body-sm text-[12px] text-outline hover:text-on-surface-variant transition-colors">
                  <span class="material-symbols-outlined text-[14px]">download</span>
                  <span>Download .circ</span>
                </a>
              </div>
              
              <!-- XML Inspector -->
              <details class="mt-4 border-t border-surface-container-high pt-3" id="xml-details">
                <summary class="cursor-pointer flex items-center gap-2 font-label-mono text-[11px] text-on-surface-variant hover:text-on-surface outline-none select-none">
                  <span class="material-symbols-outlined text-[14px]">code</span>
                  <span>View Generated XML</span>
                </summary>
                <div class="mt-2 p-2 bg-inverse-surface text-inverse-on-surface rounded font-label-mono text-[10px] overflow-auto max-h-48">
                  <pre id="xml-code-view">&lt;!-- No circuit generated yet --&gt;</pre>
                </div>
              </details>
            </div>

            <!-- Interactive Test Board -->
            <div class="rounded-xl bg-surface-container-lowest p-5 sm:p-6 shadow-sm border border-surface-container-high">
              <div class="flex items-center justify-between mb-4">
                <div>
                  <h3 class="font-headline-sm text-headline-sm text-on-surface">Interactive Pin Board</h3>
                  <p class="font-body-sm text-body-sm text-on-surface-variant">Click any pin below to poke its live switch in Logisim.</p>
                </div>
                <span id="pin-count-badge" class="px-2 py-1 bg-surface-container rounded-full text-[10px] font-label-mono font-bold text-on-surface-variant">0 Pins</span>
              </div>
              
              <div id="pins-grid" class="flex flex-col gap-3">
                <div id="empty-pins-notice" class="p-4 text-center bg-surface-container-low rounded-lg text-on-surface-variant text-[13px]">
                  <span>Generate a circuit to see interactive pins.</span>
                </div>
              </div>
              
              <div class="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-surface-container-high">
                <button id="btn-tick" class="py-2 rounded-lg bg-surface-container-low hover:bg-surface-container-high transition-colors font-body-sm text-[12px] font-medium text-on-surface flex flex-col items-center justify-center gap-1" type="button">
                  <span class="material-symbols-outlined text-[16px] text-primary">step_next</span>
                  <span>Tick</span>
                </button>
                <button id="btn-clock" class="py-2 rounded-lg bg-surface-container-low hover:bg-surface-container-high transition-colors font-body-sm text-[12px] font-medium text-on-surface flex flex-col items-center justify-center gap-1" type="button">
                  <span class="material-symbols-outlined text-[16px] text-secondary">update</span>
                  <span>Auto-Tick</span>
                </button>
                <button id="btn-reset" class="py-2 rounded-lg bg-surface-container-low hover:bg-surface-container-high transition-colors font-body-sm text-[12px] font-medium text-on-surface flex flex-col items-center justify-center gap-1" type="button">
                  <span class="material-symbols-outlined text-[16px] text-error">restart_alt</span>
                  <span>Reset</span>
                </button>
              </div>
            </div>
            
            <div id="diagnostic-card" class="rounded-xl bg-surface-container-lowest p-5 shadow-sm border border-surface-container-high flex flex-col gap-3">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-[18px] text-on-surface-variant">desktop_windows</span>
                <h4 class="font-headline-sm text-headline-sm text-on-surface">Logisim Diagnostic View</h4>
              </div>
              <div id="screenshot-container" class="w-full bg-surface-container-low rounded-lg overflow-hidden flex items-center justify-center min-h-[120px] border border-surface-container relative">
                <div class="screenshot-placeholder text-center p-4 flex flex-col items-center gap-2 text-on-surface-variant opacity-70">
                  <span class="material-symbols-outlined text-2xl">image_not_supported</span>
                  <span class="text-[11px] font-label-mono">Screenshots captured on-demand.</span>
                </div>
                <img id="live-screenshot-img" class="hidden absolute inset-0 w-full h-full object-cover" alt="Logisim window crop">
              </div>
              <div class="flex justify-between items-center">
                 <span id="test-result-badge" class="hidden px-2 py-1 text-[10px] font-bold rounded uppercase"></span>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  </main>

  <!-- Modals will be appended below (keeping original modal HTML for now) -->
  <div class="modal-overlay hidden" id="settings-modal" style="position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 100; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px);">
    <div class="modal-card bg-surface-container-lowest rounded-xl shadow-2xl p-6 w-full max-w-lg border border-surface-container-high relative">
      <button id="close-settings-btn" class="absolute top-4 right-4 text-on-surface-variant hover:text-on-surface"><span class="material-symbols-outlined">close</span></button>
      <h2 class="text-xl font-headline-md font-bold mb-4">Settings & AI Credentials</h2>
      <form id="settings-form" class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <label class="text-sm font-semibold">Active AI Provider</label>
          <select id="cfg-provider-select" class="p-2 rounded border border-surface-container-high bg-surface-container-low">
            <option value="gemini">Google Gemini</option>
            <option value="groq">Groq LPU</option>
          </select>
        </div>
        <div id="gemini-settings-group" class="flex flex-col gap-4">
          <div class="flex flex-col gap-1">
            <label class="text-sm font-semibold">Gemini API Key</label>
            <input type="password" id="cfg-api-key" class="p-2 rounded border border-surface-container-high bg-surface-container-low" placeholder="AIza...">
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-sm font-semibold">Gemini Model</label>
            <select id="cfg-model-select" class="p-2 rounded border border-surface-container-high bg-surface-container-low">
              <option value="gemini-3.6-flash">Gemini 3.6 Flash</option>
              <option value="gemini-3.5-flash">Gemini 3.5 Flash</option>
              <option value="gemini-3.8-flash">Gemini 3.8 Flash</option>
              <option value="custom">Custom Model...</option>
            </select>
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-sm font-semibold">Reasoning Budget</label>
            <select id="cfg-thinking-budget" class="p-2 rounded border border-surface-container-high bg-surface-container-low">
              <option value="1024">Balanced (~3-4s)</option>
              <option value="2048">Deep Reasoning (~5-8s)</option>
              <option value="0">Instant (~1-2s)</option>
            </select>
          </div>
        </div>
        
        <div id="groq-settings-group" class="flex flex-col gap-4 hidden">
          <div class="flex flex-col gap-1">
            <label class="text-sm font-semibold">Groq API Key</label>
            <input type="password" id="cfg-groq-key" class="p-2 rounded border border-surface-container-high bg-surface-container-low" placeholder="gsk_...">
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-sm font-semibold">Groq Model</label>
            <select id="cfg-groq-model-select" class="p-2 rounded border border-surface-container-high bg-surface-container-low">
              <option value="qwen/qwen3.8-27b">Qwen 3.8 27B</option>
              <option value="llama-3.3-70b-versatile">Llama 3.3 70B</option>
              <option value="custom">Custom Model...</option>
            </select>
          </div>
        </div>

        <div id="custom-model-group" class="flex flex-col gap-1 hidden">
          <label class="text-sm font-semibold">Custom Model ID</label>
          <input type="text" id="cfg-custom-model" class="p-2 rounded border border-surface-container-high bg-surface-container-low">
        </div>

        <hr class="border-surface-container-high">
        
        <div class="flex flex-col gap-1">
          <label class="text-sm font-semibold">Logisim Path</label>
          <input type="text" id="cfg-logisim-path" class="p-2 rounded border border-surface-container-high bg-surface-container-low" placeholder="Auto-detected">
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="flex flex-col gap-1">
            <label class="text-sm font-semibold">Offset X</label>
            <input type="number" id="cfg-offset-x" class="p-2 rounded border border-surface-container-high bg-surface-container-low" value="200">
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-sm font-semibold">Offset Y</label>
            <input type="number" id="cfg-offset-y" class="p-2 rounded border border-surface-container-high bg-surface-container-low" value="70">
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-4">
          <button type="button" id="cancel-settings-btn" class="px-4 py-2 rounded text-on-surface hover:bg-surface-container">Cancel</button>
          <button type="submit" id="save-settings-btn" class="px-4 py-2 rounded bg-primary text-on-primary">Save Changes</button>
        </div>
      </form>
    </div>
  </div>

  <div class="modal-overlay hidden" id="update-modal" style="position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 100; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px);">
    <div class="modal-card bg-surface-container-lowest rounded-xl shadow-2xl p-6 w-full max-w-md border border-surface-container-high relative">
      <button id="close-update-btn" class="absolute top-4 right-4 text-on-surface-variant hover:text-on-surface"><span class="material-symbols-outlined">close</span></button>
      <h3 class="text-xl font-headline-md font-bold mb-2">🚀 Update Available</h3>
      <p class="text-sm text-on-surface-variant mb-4">A new version of LogiMate (<span id="current-installed-ver">1.6.0</span> installed) is available on GitHub!</p>
      <div id="update-notes-preview" class="p-3 bg-surface-container-low rounded text-xs text-on-surface-variant mb-4 whitespace-pre-wrap max-h-32 overflow-auto"></div>
      <div class="flex justify-end gap-3">
        <button id="dismiss-update-btn" class="px-4 py-2 rounded text-on-surface hover:bg-surface-container text-sm">Later</button>
        <button id="btn-open-update-link" class="px-4 py-2 rounded bg-primary text-on-primary text-sm font-semibold shadow-md hover:bg-primary-container hover:text-on-primary-container">Download Update</button>
      </div>
    </div>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
"""

with open("f:/original final downloads/logism ai control/ui/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("index.html rewritten successfully!")
