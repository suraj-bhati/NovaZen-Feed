<div align="center">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/NovaZen-Feed-blueviolet%3Fstyle%3Dfor-the-badge" alt="NovaZen Feed Title"/>
<p align="center">
A robust, high-performance Python script for generating Google Shopping-compatible XML product feeds directly from a WooCommerce MySQL database.
</p>
</div>

<div align="center">

</div>

NovaZen Feed solves a critical problem for large WooCommerce stores: generating massive product feeds without crashing your server. Standard plugins can be slow and memory-intensive, leading to timeouts and frustration. By connecting directly to the database and streaming data, NovaZen provides a lightning-fast, reliable, and fully automated solution.

✨ Key Features
🚀 Extreme Performance: Bypasses the slow WordPress PHP environment for maximum speed. Perfect for stores with 100,000+ products.

🧠 Low Memory Usage (Streaming): Processes and writes the XML feed incrementally, keeping RAM usage minimal regardless of catalog size.

🔧 Highly Configurable:

config.json: Easily manage database credentials, file paths, and regional settings (tax/shipping for any country).

feed_mapping.json: Get total control over the final XML structure. Add, remove, or change any product attribute without touching the core script.

🤖 Robust Automation with systemd: Runs as a proper background service. It's more resilient than a simple cron job and automatically restarts on failure.

🛡️ Server-Safe Operation: Intelligently pauses between processing chunks to prevent server overload and website timeouts (like Cloudflare 524 errors).

📸 Advanced Data Fetching: Includes built-in logic to:

Only include products that have a featured image.

Fetch up to 3 additional product gallery images.

Correctly handle simple and variable products.

📊 Intelligent Logging & Testing:

Provides a beautiful, animated progress bar for manual runs.

Generates detailed, summary-based logs for background service runs.

Includes a "Test Mode" to quickly generate a small sample feed.

✅ Permission Handling: Automatically sets the correct file ownership and permissions on the final feed file to prevent "Restricted Access" errors in Google Merchant Center.

📁 Project Structure
/novazen-feed
│
├── 📄 config.json             # All your configurations and credentials
├── 🐍 feed_generator.py       # The main, well-commented Python script
├── 🗺️ feed_mapping.json       # Defines the XML feed structure
├── 📜 restart.sh              # A helper script to easily restart the service
├── 📝 README.md               # This file
├── 📦 requirements.txt        # Required Python libraries
│
├── 📁 logs/                   # (Created automatically)
│   └── feed_generation.log # Persistent logs for each run
│
└── 📁 output/                  # (Example directory if not using an absolute path)
    └── feed.xml            # The generated XML feed

🛠️ Installation & Setup
Follow these steps to get NovaZen Feed running on your Linux server.

1. Clone the Repository
git clone [https://github.com/your-username/novazen-feed.git](https://github.com/your-username/novazen-feed.git)
cd novazen-feed

2. Set Up Python Environment
It's highly recommended to use a virtual environment to keep dependencies isolated.

# Create the virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

3. Install Dependencies
pip install -r requirements.txt

4. Configure the Project
config.json: Open this file and fill in your database credentials, file paths, and regional settings.

feed_mapping.json: Customize the XML structure if needed. The default is already optimized for Google Shopping.

5. Set Up the System Service
This will automate the script to run in the background.

Create the Service File:

sudo tee /etc/systemd/system/novazen_feed.service > /dev/null <<'EOF'
[Unit]
Description=NovaZen Feed Generator Service
After=network.target mysql.service

[Service]
User=your_username
Group=your_username
Type=simple
WorkingDirectory=/path/to/novazen-feed
ExecStart=/path/to/novazen-feed/venv/bin/python3 /path/to/novazen-feed/feed_generator.py
Restart=on-failure
RestartSec=30s

[Install]
WantedBy=multi-user.target
EOF

Important: Replace your_username with your Linux username and /path/to/novazen-feed with the full, absolute path to this project directory.

Create the Timer File:
This sets the daily schedule.

sudo tee /etc/systemd/system/novazen_feed.timer > /dev/null <<'EOF'
[Unit]
Description=Timer to run NovaZen Feed daily at 3 AM

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

6. Enable and Start Automation
# Reload systemd to recognize the new files
sudo systemctl daemon-reload

# Enable the timer to start on boot
sudo systemctl enable novazen_feed.timer

# Start the timer to begin the schedule
sudo systemctl start novazen_feed.timer

🚀 Usage
The system is now fully automated! Here are some commands to manage it.

Run the Feed Generation Immediately:
(Make the script executable first: chmod +x restart.sh)

./restart.sh

Check the Automatic Schedule:

sudo systemctl list-timers

View the Live Logs:

sudo journalctl -u novazen_feed.service -f

📜 License
This project is licensed under the MIT License. See the LICENSE file for details.
