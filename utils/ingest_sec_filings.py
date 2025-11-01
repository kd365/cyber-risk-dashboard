import os
import requests
import time
from bs4 import BeautifulSoup
import csv
import boto3
from weasyprint import HTML


SEC_BASE = "https://data.sec.gov"
HEADERS = {"User-Agent": os.getenv("USER_AGENT", "DefaultUser default@example.com")}

def convert_html_to_pdf(html_path, pdf_path):
    HTML(html_path).write_pdf(pdf_path)
    print(f"[✓] Converted {html_path} to {pdf_path}")

def upload_to_s3(local_path, bucket_name, s3_key):
    s3 = boto3.client("s3")
    s3.upload_file(local_path, bucket_name, s3_key)
    print(f"[✓] Uploaded to s3://{bucket_name}/{s3_key}")

def get_cik(ticker):
    """Convert ticker to CIK using SEC mapping."""
    url = f"https://www.sec.gov/files/company_tickers.json"
    res = requests.get(url, headers=HEADERS)
    data = res.json()
    for entry in data.values():
        if entry["ticker"].lower() == ticker.lower():
            return str(entry["cik_str"]).zfill(10)
    return None

def fetch_sec_filings(ticker, form_type="10-K", count=3):
    """Download recent SEC filings (10-K or 10-Q) for a given ticker."""
    cik = get_cik(ticker)
    if not cik:
        print(f"[!] CIK not found for {ticker}")
        return

    url = f"{SEC_BASE}/submissions/CIK{cik}.json"
    res = requests.get(url, headers=HEADERS)
    filings = res.json()["filings"]["recent"]

    for i, form in enumerate(filings["form"]):
        if form != form_type:
            continue
        accession = filings["accessionNumber"][i].replace("-", "")
        doc_url = f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{accession}/index.json"
        doc_res = requests.get(doc_url, headers=HEADERS)
        if doc_res.status_code != 200:
            continue
        files = doc_res.json()["directory"]["item"]
        html_files = [f for f in files if f["name"].endswith(".htm")]
        if html_files:
            filename = f"{ticker}_{form_type}_{i}.html"
            html_path = f"data/raw/{filename}"
            pdf_filename = filename.replace(".html", ".pdf")
            pdf_path = f"assets/artifacts/{pdf_filename}"
            s3_key = f"raw/sec/{pdf_filename}"
            bucket_name = "cyber-risk-artifacts "

            # Save HTML
            file_url = f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{accession}/{html_files[0]['name']}"
            text = requests.get(file_url, headers=HEADERS).text
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"[✓] Saved {form_type} for {ticker} to {html_path}")

        # Convert to PDF
            convert_html_to_pdf(html_path, pdf_path)

        # Upload to S3
            upload_to_s3(pdf_path, bucket_name, s3_key)
            s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

        # Log artifact
            log_artifact(
                ticker=ticker,
                type_=form_type,
                filename=s3_url,
                source="SEC",
                date=filings["filingDate"][i]
            )
        time.sleep(0.5)


def get_cybersecurity_tickers(limit=20):
    """Return tickers of companies with 'cybersecurity' in their name or description."""
    url = "https://www.sec.gov/files/company_tickers_exchange.json"
    res = requests.get(url, headers=HEADERS)
    data = res.json()
    cyber_tickers = []

    for entry in data.values():
        name = entry["title"].lower()
        if "cyber" in name or "security" in name or "identity" in name:
            cyber_tickers.append(entry["ticker"])
        if len(cyber_tickers) >= limit:
            break
    return cyber_tickers



def log_artifact(ticker, type_, filename, source, date, log_path="data/processed/artifacts.csv"):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    header = ["ticker", "type", "filename", "source", "date"]
    row = [ticker, type_, filename, source, date]

    # Create file with header if it doesn't exist
    if not os.path.exists(log_path):
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)

    # Append new row
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)

def update_progress(ticker, step, total, message):
    progress = int((step / total) * 100)
    status = {
        "ticker": ticker,
        "progress": progress,
        "message": message,
	"running": True
    }
    with open("data/status_sec.json", "w") as f:
        json.dump(status, f)



def main():
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("assets/artifacts", exist_ok=True)

    tickers = get_cybersecurity_tickers(limit=20)
    total_steps = len(tickers) * 2  # 10-K and 10-Q per ticker
    current_step = 0

    for ticker in tickers:
        update_progress(ticker, current_step, total_steps, f"Fetching 10-K for {ticker}...")
        fetch_sec_filings(ticker, form_type="10-K")
        current_step += 1

        update_progress(ticker, current_step, total_steps, f"Fetching 10-Q for {ticker}...")
        fetch_sec_filings(ticker, form_type="10-Q")
        current_step += 1

    update_progress("Done", total_steps, total_steps, "SEC ingestion complete.")
if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)
    main()
    with open("data/status_sec.json", "w") as f:
        json.dump({
            "type": "sec",
            "progress": 100,
            "message": "Ingestion complete.",
            "running": False
        }, f)
