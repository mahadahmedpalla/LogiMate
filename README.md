# ⚡ AI Logisim Controller

> Autonomous, hybrid AI companion for **Logisim 2.7.1** powered by Google Gemini.

Eliminates slow, screenshot-based vision loops by combining:
1. **Instant XML Circuit Synthesis**: Generates pixel-perfect `.circ` files with clean orthogonal routing in $<100\text{ ms}$.
2. **Zero-Vision Coordinate Poking**: Mathematically translates component canvas coordinates to screen pixels for instantaneous pin flipping.
3. **Hardware Keyboard Automation**: Triggers Logisim simulation controls (`Ctrl+T`, `Ctrl+K`, `Ctrl+R`) with zero latency.
4. **On-Demand Diagnostic Vision**: Captures screenshots only when troubleshooting or explicitly requested.

---

## 🚀 Quick Start

### 1. Run Directly
```bash
# Install dependencies
pip install -r requirements.txt

# Launch application
python run.py
```
This will start the local server and automatically open the dashboard in your default browser at `http://localhost:8000`.

### 2. Configure Your Gemini Credentials
1. Click **Settings** (top right of the dashboard).
2. Enter your Google Gemini API key or Bearer token (supports `AIza...` and `AQ.Ab8RN6IY...`).
3. Select your desired model:
   - **Gemini 3.8 Flash**
   - **Gemini 3.7 Flash**
   - **Gemini 3.6 Flash**
   - **Gemini 2.5 Flash**
   - **Gemini 2.0 Flash**
   - **Custom Model** (type any identifier)
4. Click **Test API Connection** to verify, then **Save Changes**.

---

## 🎯 Distributing as an `.exe` for Your Website

To package this app into a standalone Windows executable that anyone visiting your website can download:

```bash
python build_exe.py
```
The compiled application will be generated in `dist/AI_Logisim_Controller/AI_Logisim_Controller.exe`. Users can simply unzip/download it and run it directly without installing Python.

---

## 🧩 Architectural Highlights

- **`logisim_engine/circ_builder.py`**: Pure Python builder for Logisim 2.7.1 schema with component library and Manhattan right-angle wire routing.
- **`logisim_engine/driver.py`**: Native Windows window discovery (`pygetwindow`), focus restoration, coordinate conversion, and keystroke simulator.
- **`agent/controller_agent.py`**: High-level agent coordinating between user natural language intent, circuit synthesis, and driver operations.
- **`ui/`**: Responsive glassmorphism dashboard built with modern CSS and vanilla JS, providing real-time pin boards, manual overrides, and execution logs.
