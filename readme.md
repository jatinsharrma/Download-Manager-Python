# 🚀 Advanced Download Manager
A high-performance, fragment-based download manager with concurrent downloading capabilities, built with Python and asyncio.

✂️ Splits large files into multiple fragments for concurrent downloading

⚡ High Performance: Up to 8x faster downloads compared to single-threaded downloading

📊 Real-time Progress Tracking: Multiple progress display styles (inline, full-screen, simple)

🔒 SSL Support: Configurable SSL certificate verification for secure downloads

🔄 Intelligent Retry: Exponential backoff retry mechanism for failed fragments

⚙️ Flexible Configuration: JSON-based configuration with CLI overrides

🖥️ Cross-platform: Works on Windows, Linux, and macOS

📱 Multiple Display Modes: Choose between different progress visualization styles

🛡️ Error Handling: Graceful fallback to single-threaded download when needed

### 📦 Installation
Prerequisites
- Python 3.8 or higher
- pip package manager

Install Dependencies
```bash
pip install aiohttp aiofiles certifi
```
Or using requirements file:

```bash
pip install -r requirements.txt
```
Download the Project
```bash
git clone https://github.com/jatinsharrma/Download-Manager-Python.git
cd advanced-download-manager
```
## 🚀 Quick Start
 Basic Download
```bash
python main.py download "https://example.com/largefile.zip"
```
Download with Custom Filename
```bash
python main.py download "https://example.com/file.zip" -f "my_download.zip"
View Configuration
```
```bash
python main.py config --show
```
## 📖 Detailed Usage
Download Commands
```bash
# Basic download
python main.py download "https://example.com/file.zip"

# Download with custom filename
python main.py download "https://example.com/file.zip" -f "custom_name.zip"

# Download without progress display
python main.py download "https://example.com/file.zip" --no-progress

## Download with specific progress style
python main.py download "https://example.com/file.zip" --progress-style simple
```
Configuration Management
```bash
# Show current configuration
python main.py config --show

# Set maximum concurrent fragments
python main.py config --fragments 8

# Configure timeout and retry attempts
python main.py config --timeout 60 --retry-attempts 5

# Set custom directories
python main.py config --output-dir "/path/to/downloads" --temp-dir "/path/to/temp"

# SSL configuration
python main.py config --no-ssl-verify  # Disable SSL verification
python main.py config --ssl-verify     # Enable SSL verification

# Progress display options
python main.py config --progress-style inline      # Inline updates (default)
python main.py config --progress-style full_screen # Full screen display
python main.py config --progress-style simple      # Minimal output

# Save configuration permanently
python main.py config --fragments 6 --timeout 45 --save
```
## ⚙️ Configuration
Configuration File
The download manager uses a download_config.json file for persistent settings:

```json
{
  "max_concurrent_fragments": 4,
  "chunk_size": 8192,
  "timeout": 30,
  "retry_attempts": 3,
  "output_directory": "./downloads",
  "temp_directory": "./temp",
  "verify_ssl": true,
  "show_progress": true,
  "progress_style": "inline"
}
```

### Configuration Parameters
| Parameter               | Description                        | Default         | Recommended Range         |
|-------------------------|------------------------------------|-----------------|--------------------------|
| `max_concurrent_fragments` | Number of simultaneous downloads   | 4               | 2–8                      |
| `chunk_size`            | Bytes per chunk                    | 8192            | 4096–65536               |
| `timeout`               | Request timeout (seconds)          | 30              | 30–120                   |
| `retry_attempts`        | Retries per failed fragment        | 3               | 3–10                     |
| `output_directory`      | Final download location            | `./downloads`   | Any valid path           |
| `temp_directory`        | Temporary fragment storage         | `./temp`        | Fast storage preferred   |
| `verify_ssl`            | SSL certificate verification       | true            | true (false for testing) |
| `show_progress`         | Display download progress          | true            | true/false               |
| `progress_style`        | Progress display type              | `inline`        | inline/full_screen/simple|


### Performance Tuning
#### For Fast Internet (100+ Mbps):

```bash
python main.py config --fragments 8 --chunk-size 32768 --timeout 30 --save
```

#### For Slow/Unreliable Internet:

```bash
python main.py config --fragments 2 --chunk-size 4096 --timeout 120 --retry-attempts 10 --save
```

### 🏗️ Project Structure
```text
advanced-download-manager/
├── main.py              # Entry point and CLI argument parsing
├── core.py              # Core download logic (FragmentDownloader)
├── cli.py               # Command-line interface (DownloadManagerCLI)
├── progress.py          # Progress tracking and display (ProgressTracker)
├── config.py            # Configuration management (DownloadConfig)
├── requirements.txt     # Python dependencies
├── download_config.json # Configuration file (auto-generated)
├── downloads/           # Default download directory
├── temp/               # Temporary fragment storage
└── README.md           # This file
🔧 Requirements
```

### Python Dependencies
```text
aiohttp>=3.8.0
aiofiles>=22.1.0
certifi>=2022.12.7
```

### System Requirements
- Python: 3.8 or higher

- Memory: Minimum 512MB RAM

- Storage: Space for temporary fragments (2x file size recommended)

- Network: Any internet connection

### 📊 Progress Display Styles
#### 1. Inline Progress (Default)
Updates the same lines in place, perfect for most terminals:

```text
Overall: [████████████████░░░░░░░░░░░░░░] 67.3% | 1.2 GB/1.8 GB
Frag  1: [██████████████████████████████] 100.0% | 15.2 MB/s
Frag  2: [███████████████████░░░░░░░░░░░░]  65.4% | 12.8 MB/s
Frag  3: [████████████████░░░░░░░░░░░░░░░]  55.2% | 14.1 MB/s
Frag  4: [██████████░░░░░░░░░░░░░░░░░░░░░]  34.8% | 11.5 MB/s
```

#### 2. Full Screen Progress
Clears entire screen for updates (requires ANSI support):

```text
============================================================
DOWNLOAD PROGRESS - 14:30:25
============================================================
Overall: [████████████████░░░░░░░░░░░░░░] 67.3%
Downloaded: 1.2 GB / 1.8 GB
Total Speed: 53.7 MB/s

Fragment Progress:
------------------------------------------------------------
✓ Fragment  1: [██████████████████████████████] 100.0% |   15.2 MB/s
↓ Fragment  2: [███████████████████░░░░░░░░░░░░]  65.4% |   12.8 MB/s
↓ Fragment  3: [████████████████░░░░░░░░░░░░░░░]  55.2% |   14.1 MB/s
↓ Fragment  4: [██████████░░░░░░░░░░░░░░░░░░░░░]  34.8% |   11.5 MB/s
============================================================
```

#### 3. Simple Progress
Minimal output, updates only on significant progress changes:

```text
Progress:  25.0% | Speed: 45.2 MB/s | Fragments: 1/4 completed
Progress:  50.0% | Speed: 48.7 MB/s | Fragments: 2/4 completed
Progress:  75.0% | Speed: 52.1 MB/s | Fragments: 3/4 completed
Progress: 100.0% | Speed: 49.8 MB/s | Fragments: 4/4 completed
```
### 🛠️ Troubleshooting
#### Common Issues
#### SSL Certificate Errors
```bash
# Temporarily disable SSL verification
python main.py config --no-ssl-verify

# Download the file
python main.py download "https://problematic-site.com/file.zip"

# Re-enable SSL verification
python main.py config --ssl-verify --save
```

#### Server Doesn't Support Range Requests
Some servers don't support fragment downloading. The manager automatically falls back to single-threaded download.

#### Progress Display Issues
If progress bars are not updating properly:

```bash
# Try simple progress style
python main.py config --progress-style simple --save

# Or disable progress entirely
python main.py config --no-progress --save
```

#### Slow Downloads
```bash
# Increase concurrent fragments (test with your connection)
python main.py config --fragments 6 --save

# Increase chunk size for better throughput
python main.py config --chunk-size 16384 --save

# Increase timeout for slow servers
python main.py config --timeout 60 --save
```

#### Debug Information
To get detailed debug information:

```python
# Add to get_file_size method in core.py
print(f"DEBUG: Status: {response.status}")
print(f"DEBUG: Headers: {dict(response.headers)}")
```
### 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

Development Setup
1. Fork the repository
2. Create a feature branch (git checkout -b feature/amazing-feature)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (git commit -m 'Add amazing feature')
6. Push to the branch (git push origin feature/amazing-feature)
7. Open a Pull Request

### 📝 License
This project is licensed under the MIT License.

### 🙏 Acknowledgments
- Built with aiohttp for async HTTP requests
- Uses aiofiles for async file operations
- SSL certificate handling via certifi

### 📈 Performance Benchmarks
Typical performance improvements over single-threaded downloads:

| Connection Speed | Fragments | Typical Speedup      |
|------------------|-----------|----------------------|
| 100 Mbps         | 4         | 3–4× faster          |
| 500 Mbps         | 6         | 5–6× faster          |
| 1 Gbps           | 8         | 7–8× faster          |

Results may vary based on server capabilities and network conditions.


## Future Work
- Implement GUI

Happy Downloading! 🚀