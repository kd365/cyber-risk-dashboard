import os
import re

RAW_DIR = "data/raw/transcripts"
CLEAN_DIR = "data/clean/transcripts"

def clean_transcript(text):
    # Remove disclaimers and ads
    text = re.sub(r"(This article is a transcript.*?Copyright.*?Motley Fool)", "", text, flags=re.DOTALL)
    # Remove speaker labels
    text = re.sub(r"[A-Z][a-z]+ [A-Z][a-z]+ - .*?:", "", text)
    # Normalize whitespace
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
    return text

def process_transcripts():
    os.makedirs(CLEAN_DIR, exist_ok=True)
    for file in os.listdir(RAW_DIR):
        if not file.endswith(".txt"):
            continue
        raw_path = os.path.join(RAW_DIR, file)
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        clean_text = clean_transcript(raw_text)
        clean_path = os.path.join(CLEAN_DIR, file)
        with open(clean_path, "w", encoding="utf-8") as f:
            f.write(clean_text)
        print(f"[✓] Cleaned transcript: {file}")

if __name__ == "__main__":
    process_transcripts()
