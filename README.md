<div align="center">
  <img src="https://img.shields.io/badge/NovaZen-Feed-blueviolet?style=for-the-badge" alt="NovaZen Feed Title"/>
  <p align="center">
    A robust, high-performance Python script for generating Google Shopping-compatible XML product feeds directly from a WooCommerce MySQL database.
  </p>
</div>

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg?style=flat-square)
![Project Status](https://img.shields.io/badge/status-production_ready-brightgreen.svg?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)

</div>

---

**NovaZen Feed** solves a critical problem for large WooCommerce stores: generating massive product feeds without crashing your server. Standard plugins can be slow and memory-intensive, leading to timeouts and frustration. By connecting directly to the database and streaming data, NovaZen provides a lightning-fast, reliable, and fully automated solution.

## ✨ Key Features

* **🚀 Extreme Performance:** Bypasses the slow WordPress PHP environment for maximum speed. Perfect for stores with 100,000+ products.
* **🧠 Low Memory Usage (Streaming):** Processes and writes the XML feed incrementally, keeping RAM usage minimal regardless of catalog size.
* **🔧 Highly Configurable:**
    * **`config.json`**: Easily manage database credentials, file paths, and regional settings (tax/shipping for any country).
    * **`feed_mapping.json`**: Get total control over the final XML structure. Add, remove, or change any product attribute without touching the core script.
* **🤖 Robust Automation with `systemd`:** Runs as a proper background service. It's more resilient than a simple cron job and automatically restarts on failure.
* **🛡️ Server-Safe Operation:** Intelligently pauses between processing chunks to prevent server overload and website timeouts (like Cloudflare 524 errors).
* **📸 Advanced Data Fetching:** Includes built-in logic to:
    * Only include products that have a featured image.
    * Fetch up to 3 additional product gallery images.
    * Correctly handle simple and variable products.
* **📊 Intelligent Logging & Testing:**
    * Provides a beautiful, animated progress bar for manual runs.
    * Generates detailed, summary-based logs for background service runs.
    * Includes a "Test Mode" to quickly generate a small sample feed.
* **✅ Permission Handling:** Automatically sets the correct file ownership and permissions on the final feed file to prevent "Restricted Access" errors in Google Merchant Center.

## 📁 Project Structure
