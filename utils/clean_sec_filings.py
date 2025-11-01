import os
from bs4 import BeautifulSoup

RAW_DIR = "data/raw"
CLEAN_DIR = "data/clean/sec"

def clean_html_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    text = soup.get_text(separator="\n")
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
    return text

def process_sec_filings():
    os.makedirs(CLEAN_DIR, exist_ok=True)
    for file in os.listdir(RAW_DIR):
        if not file.endswith(".html"):
            continue
        raw_path = os.path.join(RAW_DIR, file)
        clean_text = clean_html_file(raw_path)
        clean_path = os.path.join(CLEAN_DIR, file.replace(".html", ".txt"))
        with open(clean_path, "w", encoding="utf-8") as f:
            f.write(clean_text)
        print(f"[✓] Cleaned SEC filing: {file}")

if __name__ == "__main__":
    process_sec_filings()
