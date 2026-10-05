import re

# 1. Update style.css to handle dynamic class overrides correctly
style_css = """/* LogiMate Light Theme Tailwind Overrides */

body {
  margin: 0;
  padding: 0;
  overflow-x: hidden;
  overscroll-behavior-y: none;
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #c7c4d7;
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #777586;
}

/* Base utility overrides */
.hidden {
  display: none !important;
}

/* SVG Rendering specifics (overrides Logisim raw SVG) */
.schematic-svg text {
  user-select: none;
}

/* Dynamic Classes from app.js */
.status-dot {
  width: 8px; height: 8px; border-radius: 9999px; display: inline-block; transition: background-color 0.3s;
}
.status-dot.searching { background-color: #facc15; animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
.status-dot.connected { background-color: #10b981; }
.status-dot.error { background-color: #ef4444; }

.api-key-badge {
  padding: 0.125rem 0.375rem; border-radius: 0.25rem; font-size: 10px; text-transform: uppercase; font-weight: bold;
  background-color: rgba(239, 68, 68, 0.1); color: #ef4444;
}
.api-key-badge.set {
  background-color: rgba(16, 185, 129, 0.1); color: #10b981;
}

.status-pill-small {
  font-weight: 600; font-size: 10px; letter-spacing: 0.05em; text-transform: uppercase;
  color: #777586;
}
.status-pill-small.ready {
  color: #10b981;
}
"""

with open("f:/original final downloads/logism ai control/ui/style.css", "w", encoding="utf-8") as f:
    f.write(style_css)

# 2. Update index.html for scrolling layout and missing settings button
with open("f:/original final downloads/logism ai control/ui/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Fix layout scrolling
html = html.replace('<main class="w-full pt-16 bg-surface min-h-[calc(100vh-4rem)]">', 
                    '<main class="w-full pt-16 bg-surface h-[calc(100vh-4rem)] overflow-hidden">')
html = html.replace('<div class="flex flex-col w-full">', 
                    '<div class="flex flex-col w-full h-full">')
html = html.replace('<div class="w-full max-w-7xl mx-auto px-6 lg:px-10 py-8 flex flex-col gap-8">', 
                    '<div class="w-full max-w-7xl mx-auto px-6 lg:px-10 py-6 flex flex-col gap-4 h-full">')
html = html.replace('<div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">', 
                    '<div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start h-full overflow-hidden">')

# Left column
html = html.replace('<div class="lg:col-span-7 flex flex-col gap-6">', 
                    '<div class="lg:col-span-7 flex flex-col gap-6 h-full overflow-hidden">')
html = html.replace('<div id="chat-feed" class="flex flex-col gap-4">', 
                    '<div id="chat-feed" class="flex flex-col gap-4 flex-grow overflow-y-auto pr-2 pb-4">')

# Right column
html = html.replace('<div class="lg:col-span-5 flex flex-col gap-6">', 
                    '<div class="lg:col-span-5 flex flex-col gap-6 h-full overflow-y-auto pb-8 pr-2">')

# Fix status label colors inside app.js overrides (we'll fix app.js var(--text-primary) to match new theme)
# Add test connection button to modal
missing_test_btn = """
        <div id="custom-model-group" class="flex flex-col gap-1 hidden">
          <label class="text-sm font-semibold">Custom Model ID</label>
          <input type="text" id="cfg-custom-model" class="p-2 rounded border border-surface-container-high bg-surface-container-low">
        </div>

        <div class="flex items-center gap-3 mt-2">
          <button type="button" id="btn-test-connection" class="px-4 py-2 rounded text-on-surface-variant hover:bg-surface-container border border-surface-container-high text-sm font-medium">Test API Connection</button>
          <span id="test-result-badge" class="hidden px-2 py-1 text-[11px] font-bold rounded uppercase"></span>
        </div>

        <hr class="border-surface-container-high">
"""
html = html.replace("""        <div id="custom-model-group" class="flex flex-col gap-1 hidden">
          <label class="text-sm font-semibold">Custom Model ID</label>
          <input type="text" id="cfg-custom-model" class="p-2 rounded border border-surface-container-high bg-surface-container-low">
        </div>

        <hr class="border-surface-container-high">""", missing_test_btn)

# Make sure window status label correctly inherits color, so let's simplify index.html initial state
html = html.replace('<span id="status-dot" class="w-2 h-2 rounded-full bg-secondary animate-pulse searching"></span>', 
                    '<span id="status-dot" class="status-dot searching"></span>')
html = html.replace('<span id="api-key-badge" class="px-1.5 py-0.5 bg-error/10 text-error rounded text-[10px] uppercase font-bold">Set Key</span>',
                    '<span id="api-key-badge" class="api-key-badge">Set Key</span>')
html = html.replace('<span id="circuit-presence-pill" class="font-semibold text-[10px] tracking-wider uppercase">No Circuit</span>',
                    '<span id="circuit-presence-pill" class="status-pill-small">No Circuit</span>')

with open("f:/original final downloads/logism ai control/ui/index.html", "w", encoding="utf-8") as f:
    f.write(html)

# 3. Patch app.js var(--text-primary) to real colors
with open("f:/original final downloads/logism ai control/ui/app.js", "r", encoding="utf-8") as f:
    js = f.read()

js = js.replace('statusLabel.style.color = "var(--text-primary)";', 'statusLabel.style.color = "#141b2b"; /* on-surface */')
js = js.replace('statusLabel.style.color = "var(--text-muted)";', 'statusLabel.style.color = "#777586"; /* outline */')
js = js.replace('testResultBadge.className = "test-result-badge success";', 'testResultBadge.className = "px-2 py-1 text-[11px] font-bold rounded uppercase bg-secondary-container text-on-secondary-container";')
js = js.replace('testResultBadge.className = "test-result-badge error";', 'testResultBadge.className = "px-2 py-1 text-[11px] font-bold rounded uppercase bg-error-container text-on-error-container";')
js = js.replace('testResultBadge.className = "test-result-badge";', 'testResultBadge.className = "hidden";')

with open("f:/original final downloads/logism ai control/ui/app.js", "w", encoding="utf-8") as f:
    f.write(js)

print("All fixes applied successfully.")
