# Ubuntu Server Deployment Guide for IntelliClean AI

This guide provides a comprehensive step-by-step walkthrough to deploy the **IntelliClean AI** application on a production Ubuntu Server environment. It is compiled directly from host deployment logs, detailing setup paths, command executions, environment settings, and critical troubleshooting strategies for headless servers.

---

## 📋 System Prerequisites

* **Operating System:** Ubuntu Server (20.04 LTS, 22.04 LTS, or 24.04 LTS)
* **Python Version:** Python 3.10 or higher (Python 3.12 recommended)
* **System Hardware:** 
  * Minimum: 12GB RAM (due to local LLM model footprint)
  * Recommended: 16GB+ RAM or dedicated GPU with CUDA support for accelerated local inference.
* **Network Open Ports:** 
  * Port `8501` (Streamlit standard ingress)
  * Port `1234` (LM Studio server port - local access only, should be blocked externally)

---

## 🛠️ Step 1: Clone the Repository & Configure Workspace

First, connect to your remote Ubuntu server via SSH and clone the codebase:

```bash
# Clone the repository
git clone https://github.com/ashudsvv99/Ai-based-Data-Cleaning-and-deduplications-tool.git

# Move into the project directory
cd Ai-based-Data-Cleaning-and-deduplications-tool
```

---

## 🤖 Step 2: Set Up the Local LLM Inference Server (LM Studio CLI)

Running a graphical AppImage on a headless server will fail due to lack of a display server (`Missing X server or $DISPLAY`). To run the model offline in a production environment, we install the **LM Studio CLI Daemon (`lms`)**.

### 1. Install the CLI tool
Run the installer command using `curl`:
```bash
curl -fsSL https://lmstudio.ai/install.sh | bash
```

### 2. Configure Environment Path
The installation script creates a bin folder in your home directory. Add this path to your current shell session and append it to your bash runcom file to make it permanent:

```bash
# Temporary export for current session
export PATH="$HOME/.lmstudio/bin:$PATH"

# Persist the configuration in .bashrc
echo 'export PATH="$HOME/.lmstudio/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

> [!WARNING]
> Do not attempt to run `sudo lms ...`. The `lms` bin path is configured only for your local user. Running with `sudo` will fail with `sudo: lms: command not found`. Always run standard user commands.

### 3. Spin up the Background Daemon
Start the LM Studio daemon services in the background:
```bash
lms daemon up
```
*Expected Output:* `llmster started (PID: <pid_number>).`

### 4. Fetch the Local LLM Model
Download a lightweight, highly efficient instruct model. We recommend **Gemma 4 E2B Instruct GGUF** for systems running on limited resources:

```bash
lms get google/gemma-4-e2b
```
During the prompt, select the recommended quantized variant (e.g., `Q4_K_M`, approx. 4.41 GB) and verify the download progress reaches 100%.

### 5. Load the LLM into Memory
Load the downloaded model into the local inference engine:
```bash
lms load google/gemma-4-e2b
```

### 6. Start the API Server
Launch the local OpenAI-compatible inference server:
```bash
lms server start
```
*Expected Output:* `Success! Server is now running on port 1234`
The server now listens on `http://localhost:1234/v1`.

---

## 🐍 Step 3: Set Up Python Virtual Environment & Install Dependencies

To prevent package collision with host systems, configure a dedicated virtual environment for the application:

```bash
# Create the virtual environment
python3 -m venv denv

# Activate the virtual environment
source denv/bin/activate

# Install the dependencies from the requirements manifest
pip install -r requirements.txt
```

---

## 🚀 Step 4: Launch the Streamlit Web Application

### Common Launch Anti-Patterns (Avoid These)
1. **Running `./app.py`:** Fails with a `-bash: ./app.py: Permission denied` error.
2. **Running `python3 app.py`:** Starts the script outside the Streamlit server lifecycle, rendering streamlit's components and `session_state` useless, printing warnings:
   `Session state does not function when running a script without streamlit run`
3. **Running `streamlit -m app.py`:** Streamlit does not accept a `-m` flag. Fails with `No such option '-m'`.

### Correct Invocation
Always launch the web interface using:
```bash
streamlit run app.py
```

### Running as a Persistent Service (Production)
If you close your SSH connection, the streamlit server will stop. Run the process in the background using `nohup` or `tmux`:

#### Option A: Running with nohup
```bash
nohup streamlit run app.py > streamlit.log 2>&1 &
```

#### Option B: Running via systemd Service

Running as a systemd service is the most robust way to manage the lifecycle of your application in production. It ensures the application starts automatically when the server boots, restarts on crash, and permits standard logging.

##### 1. Create the Service Configuration File
Open your text editor as root to create the configuration file:
```bash
sudo nano /etc/systemd/system/intelliclean.service
```
Copy and paste the configuration below, replacing `<your-username>` with your actual system username:
```ini
[Unit]
Description=IntelliClean AI Web Application
After=network.target

[Service]
User=<your-username>
WorkingDirectory=/home/<your-username>/Ai-based-Data-Cleaning-and-deduplications-tool
ExecStart=/home/<your-username>/Ai-based-Data-Cleaning-and-deduplications-tool/denv/bin/streamlit run app.py
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

##### 2. Enable & Start the Service
Reload the systemd daemon to register the new configuration, then enable and start the service:
```bash
# Reload configurations
sudo systemctl daemon-reload

# Enable service to run on boot
sudo systemctl enable intelliclean.service

# Start the service immediately
sudo systemctl start intelliclean.service
```

##### 3. Example Usage & Service Management
Once the service is active, manage its execution state using standard systemctl commands:

```bash
# Check the status and confirm the process is running
sudo systemctl status intelliclean.service

# Restart the application (e.g. after updating source code)
sudo systemctl restart intelliclean.service

# Stop the application
sudo systemctl stop intelliclean.service
```

##### 4. How to Inspect Live App Logs
To view the output stream, print statements, or debug any runtime errors, use `journalctl` to inspect logs:
```bash
# View live-streamed logs (-f follows new logs)
journalctl -u intelliclean.service -f

# View the last 50 log entries
journalctl -u intelliclean.service -n 50
```

---

## 🌐 Step 5: Accessing the Application

Once launched, the Streamlit server listens on port `8501`.
* **Local access:** `http://localhost:8501`
* **External Network Access:** `http://<server-external-ip>:8501`

> [!IMPORTANT]
> If your server is hosted on a cloud provider (AWS EC2, Google Cloud, DigitalOcean, etc.), verify that your security groups, firewall policies (`ufw`), or network access control lists allow inbound traffic on TCP port `8501`.

