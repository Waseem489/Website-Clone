# Web Scraper with Selenium & BeautifulSoup

Welcome to the **Web Scraper** project! This project is designed to extract images and text data (headers, paragraphs, and links) from a website using both Selenium (for dynamic content) and BeautifulSoup (for HTML parsing).

## Features

- **Dynamic Content Handling:** Uses Selenium to load JavaScript-driven pages and scrolls the page to capture all content.
- **Image Extraction:** Automatically finds and downloads images (even from background styles) from the target website.
- **Text Extraction:** Extracts headers (h1-h6), paragraphs, and links with noise filtering to provide clean text content.
- **Organized Storage:** Saves scraped data in a structured format organized by domain. Each website will have its own folder with separate subfolders for images and data. The data folder contains:
  - `metadata.json` (complete scraped data and statistics)
  - `headers.txt` (extracted headers)
  - `paragraphs.txt` (extracted paragraphs)
  - `links.txt` (extracted links)
  - `scraping.log` (logs of the scraping process)
- **Error Handling:** Incorporates timeouts, retry mechanisms and clear logging to help diagnose issues.

## Prerequisites

- **Python 3.x**: Make sure Python 3.x is installed.
- **pip**: Package installer for Python

## Installation

1. **Clone the Repository**

   ```bash
   git clone <repository_url>
   cd web_scraper
   ```

2. **Install Dependencies**

   All required Python packages are listed in the `requirements.txt` file. Install them with:

   ```bash
   pip install -r requirements.txt
   ```

   If `requirements.txt` doesn't exist, ensure the following dependencies are installed:

   - `requests`
   - `beautifulsoup4`
   - `selenium`
   - `webdriver-manager`

## Usage

Run the scraper using the following command:

```bash
python main.py
```

When prompted, enter the URL of the website you wish to scrape. The program will:

1. Load the page using Selenium in headless mode.
2. Scroll down to load all dynamic content.
3. Extract and download images, organizing them under `data/<domain>/images`.
4. Extract text data (headers, paragraphs, and links) and save them in `data/<domain>/data`.

## Folder Structure

```
web_scraper/
├── main.py             # Main entry point
├── scraper.py          # Contains the main scraping logic
├── config.py           # Configuration settings (if any)
├── README.md           # This file
└── data/               # Directory where all scraped data is saved
    └── <domain>/       # One folder per website (e.g. pcb-factory-wwcjm2h.gamma.site)
        ├── images/     # Downloaded images
        └── data/       # Data files: metadata.json, headers.txt, paragraphs.txt, links.txt, scraping.log
```

## Logging

The scraper uses Python's built-in `logging` module. Logs are saved to `scraping.log` within the website's data folder and also printed to the console for real-time monitoring.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests for improvements or new features.

## Disclaimer

This tool is intended for educational and testing purposes. Please ensure you have permission to scrape the target websites. Respect website policies and legal guidelines.

---

Enjoy scraping and happy coding!
