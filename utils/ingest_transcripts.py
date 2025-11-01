import os
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from weasyprint import HTML
from ingest_sec_filings import get_cybersecurity_tickers
import boto3
from weasyprint import HTML

HEADERS = {"User-Agent": os.getenv("USER_AGENT", "DefaultUser default@example.com")}




tickers = get_cybersecurity_tickers
def log_artifact(ticker, type_, filename, source, date, log_path="data/processed/artifacts.csv"):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    header = ["ticker", "type", "filename", "source", "date"]
    row = [ticker, type_, filename, source, date]

    if not os.path.exists(log_path):
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)

    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)

def convert_text_to_pdf(text_path, pdf_path):
    with open(text_path, "r", encoding="utf-8") as f:
        html_content = f"<pre>{f.read()}</pre>"
    HTML(string=html_content).write_pdf(pdf_path)
    print(f"[✓] Converted {text_path} to {pdf_path}")

def upload_to_s3(local_path, bucket_name, s3_key):
    s3 = boto3.client("s3")
    s3.upload_file(local_path, bucket_name, s3_key)
    print(f"[✓] Uploaded to s3://{bucket_name}/{s3_key}")

def fetch_transcript(ticker, quarter="Q3", year="2025"):
    # Example URL structure — replace with actual source logic
    url = f"https://www.fool.com/earnings-call/{ticker}/{year}/{quarter}/"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print(f"[!] Failed to fetch transcript for {ticker}")
        return

    soup = BeautifulSoup(res.text, "html.parser")
    transcript_text = soup.get_text()

    filename = f"{ticker}_{quarter}_{year}_transcript.txt"
    text_path = f"data/raw/{filename}"
    pdf_filename = filename.replace(".txt", ".pdf")
    pdf_path = f"assets/artifacts/{pdf_filename}"
    bucket_name = "cyber-risk-artifacts"

    with open(text_path, "w", encoding="utf-8") as f:
        f.write(transcript_text)
    print(f"[✓] Saved transcript for {ticker} to {text_path}")

    convert_text_to_pdf(text_path, pdf_path)
    upload_to_s3(pdf_path, bucket_name, s3_key)
    s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

    log_artifact(
        ticker=ticker,
        type_="transcript",
        filename=pdf_filename,
        source="Motley Fool",
        date=datetime.today().strftime("%Y-%m-%d")
    )
    return True

def update_progress(ticker, step, total, message):
    progress = int((step / total) * 100)
    status = {
        "ticker": ticker,
        "progress": progress,
        "message": message,
	"running": True
    }
    with open("data/status_transcripts.json", "w") as f:
        json.dump(status, f)

def main():
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("assets/artifacts", exist_ok=True)
    tickers = ["CRWD", "ZS", "PANW", "OKTA", "NET"]  # Customize as needed
    total_steps = len(tickers)
    current_step = 0

    for ticker in tickers:
        update_progress(ticker, current_step, total_steps, f"Fetching transcript for {ticker}...")
        success = fetch_transcript(ticker)
        current_step += 1
        if not success:
            update_progress(ticker, current_step, total_steps, f"Transcript not found for {ticker}")

    update_progress("Done", total_steps, total_steps, "Transcript ingestion complete.")

if __name__ == "__main__":
    main()
    with open("data/status_transcripts.json", "w") as f:
        json.dump({
            "type": "transcripts",
            "progress": 100,
            "message": "Ingestion complete.",
            "running": False
        }, f)
