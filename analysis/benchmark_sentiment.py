from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np
import pandas as pd

MODELS = {
    "FinBERT": "yiyanghkust/finbert-tone",
    "ProsusAI FinBERT": "ProsusAI/finbert",
    "Financial-RoBERTa": "mrm8488/financial-roberta-sentiment"
}

def load_model(model_name):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    return tokenizer, model

def score_sentiment(text, tokenizer, model):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    scores = torch.nn.functional.softmax(outputs.logits, dim=-1)
    return scores[0].numpy()

def benchmark_models(text):
    results = {}
    for label, model_name in MODELS.items():
        tokenizer, model = load_model(model_name)
        scores = score_sentiment(text, tokenizer, model)
        results[label] = scores
    return results

def save_benchmark_results(texts, tickers, output_path="data/processed/sentiment_benchmark.csv"):
    rows = []
    for text, ticker in zip(texts, tickers):
        for label, model_name in MODELS.items():
            tokenizer, model = load_model(model_name)
            scores = score_sentiment(text, tokenizer, model)
            rows.append({
                "ticker": ticker,
                "model": label,
                "positive": scores[2] if len(scores) == 3 else scores[1],
                "neutral": scores[1] if len(scores) == 3 else scores[0],
                "negative": scores[0],
            })
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    print(f"[✓] Saved benchmark results to {output_path}")
