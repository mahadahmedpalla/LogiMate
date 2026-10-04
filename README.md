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
2. Enter your Google Gemini API key or Groq API key (`gsk_...`).
3. Select your desired provider and model:
   - **Google Gemini**: Gemini 3.6 Flash, 3.5 Flash, 3.1 Flash Lite, 3.8 Flash, 3.7 Flash, Custom
   - **Groq LPU**: Qwen 3.8 27B, Llama 3.3 70B, DeepSeek R1 Distill 70B, Llama 3.1 8B Instant, Custom
4. Click **Test API Connection** to verify, then **Save Changes**.

---

## 📦 Download & Install (For End Users)

1. Download the latest setup installer (`LogiMate-Setup-v1.5.0.exe`) from the [Releases Page](https://github.com/mahadahmedpalla/LogiMate/releases/latest).
2. Double-click the installer to install LogiMate with desktop shortcuts and automatic Logisim detection.

### 🛡️ Note on Windows SmartScreen ("Windows protected your PC")

When launching the installer for the first time, Microsoft Defender SmartScreen may display a blue dialog stating:
> *"Microsoft Defender SmartScreen prevented an unrecognized app from starting."*

**This is completely normal for newly released, open-source software that is not signed with an enterprise certificate. LogiMate is 100% clean, open-source, and contains zero malware.**

#### How to proceed (takes 2 seconds):
1. On the blue screen, click the underline link: **"More info"**.
2. Click the button: **"Run anyway"**.
3. The setup wizard will start immediately!

---

## 🎯 Distributing as an `.exe` for Your Website

To package this app into a standalone Windows executable and setup installer:

```bash
# 1. Compile standalone application:
python build_exe.py

# 2. Compile single-file Windows setup installer:
python build_installer.py
```
The compiled setup wizard will be created in `dist_installer/LogiMate-Setup-v1.5.0.exe`.

---

## 🧩 Architectural Highlights

- **`logisim_engine/circ_builder.py`**: Pure Python builder for Logisim 2.7.1 schema with component library and Manhattan right-angle wire routing.
- **`logisim_engine/driver.py`**: Native Windows window discovery (`pygetwindow`), focus restoration, coordinate conversion, and keystroke simulator.
- **`agent/controller_agent.py`**: High-level agent coordinating between user natural language intent, circuit synthesis, and driver operations.
- **`ui/`**: Responsive glassmorphism dashboard built with modern CSS and vanilla JS, providing real-time pin boards, manual overrides, and execution logs.
