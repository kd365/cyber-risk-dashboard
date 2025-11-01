import os
import requests
from bs4 import BeautifulSoup
import time
import glob

HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE_DIR = "data/raw/transcripts"

def get_tickers_from_sec_filings():
    """Extract tickers from filenames in SEC filings directory."""
    files = glob.glob("data/raw/*.html")
    tickers = set()
    for f in files:
        parts = os.path.basename(f).split("_")
        if parts:
            tickers.add(parts[0])
    return sorted(list(tickers))

def search_motley_fool_transcripts(ticker):
    """Search Motley Fool for recent earnings call transcripts."""
    query = f"{ticker} earnings call transcript site:fool.com"
    url = f"https://www.google.com/search?q={query}"
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    links = []

    for a in soup.select("a"):
        href = a.get("href")
        if href and "fool.com" in href and "transcript" in href:
            clean_url = href.split("&")[0].replace("/url?q=", "")
            if clean_url not in links:
                links.append(clean_url)

    return links[:3]  # Limit to 3 most recent

def download_transcript(url, ticker):
    """Download and save transcript HTML and text."""
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print(f"[!] Failed to fetch {url}")
        return

    soup = BeautifulSoup(res.text, "html.parser")
    paragraphs = soup.find_all("p")
    text = "\n".join(p.get_text() for p in paragraphs)

    os.makedirs(BASE_DIR, exist_ok=True)
    filename = os.path.join(BASE_DIR, f"{ticker}_{int(time.time())}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"[✓] Saved transcript for {ticker} to {filename}")

def main(extra_tickers=None):
    sec_tickers = get_tickers_from_sec_filings()
    all_tickers = set(sec_tickers)
    if extra_tickers:
        all_tickers.update(extra_tickers)

    print(f"[INFO] Scraping transcripts for: {sorted(all_tickers)}")

    for ticker in sorted(all_tickers):
        links = search_motley_fool_transcripts(ticker)
        for url in links:
            download_transcript(url, ticker)
            time.sleep(2)

if __name__ == "__main__":
    # Add any extra tickers here
    additional_tickers = ["NET", "S"]
    main(extra_tickers=additional_tickers)
