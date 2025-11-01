from dash.dependencies import Input, Output
from dash import html, State
import json
import subprocess
import os
import pandas as pd


def register_callbacks(app):
    with open("data/status_sec.json", "w") as f:
        json.dump({
            "type": "sec",
            "progress": 100,
            "message": "Ingestion complete.",
            "running": False
        }, f)
    @app.callback(
        Output("start-ingestion", "disabled"),
        Input("progress-poller", "n_intervals"),
        State("ingestion-type", "value")
    )
    def toggle_ingestion_button(_, selected):
        if not selected:
            return True
        for t in selected:
            try:
                with open(f"data/status_{t}.json", "r") as f:
                    status = json.load(f)
                    if status.get("running"):
                        running = True
            except:
                continue
        return False
    @app.callback(
        Output("risk-indicator-graph", "figure"),
        Input("firm-selector", "value")
    )
    def update_risk_graph(firm):
        # Load processed data and generate graph
        return {}

    @app.callback(
        Output("wordcloud-container", "children"),
        Input("firm-selector", "value")
    )
    def update_wordcloud(firm):
        return html.Div([
            html.H3("Word Cloud"),
            html.Img(src=f"/assets/wordclouds/{firm}.png", style={"width": "60%"})
        ])

    @app.callback(
        Output("risk-indicators", "children"),
        Input("firm-selector", "value")
    )
    def update_risk_indicators(firm):
        df = pd.read_csv("data/processed/risk_indicators.csv")
        risks = df[df["ticker"] == firm]["indicator"].unique()
        return html.Div([
            html.H3("Extracted Risk Indicators"),
            html.Ul([html.Li(risk) for risk in risks])
        ])

    @app.callback(
        Output("ingestion-status", "children"),
        Input("start-ingestion", "n_clicks"),
        State("user-name", "value"),
        State("user-email", "value"),
	State("ingestion-type", "value")
    )
    def run_ingestion(n_clicks, name, email, ingestion_type):
        if n_clicks == 0 or not name or not email or not ingestion_type:
            return ""

        # Save user info to a config file or pass as env vars
        os.environ["USER_AGENT"] = f"{name} {email}"
        if ingestion_type == "sec":
            subprocess.Popen(["python", "utils/ingest_sec_filings.py"])
        elif ingestion_type == "transcripts":
            subprocess.Popen(["python", "utils/ingest_transcripts.py"])

        return f"Ingestion started with user agent: {name} {email}"

    @app.callback(
        Output("progress-display", "children"),
        Input("progress-poller", "n_intervals")
    )
    def show_progress(_):
        messages = []
        for t in ["sec", "transcripts"]:
            try:
                with open(f"data/status_{t}.json", "r") as f:
                    status = json.load(f)
                    msg = f"{t.upper()} → {status.get('progress', 0)}%: {status.get('message', '')}"
                    messages.append(html.Div(msg))
            except Exception as e::
                messages.appen(html.Div(f"t.upper()} -> No status available"))
        return html.Div(messages)
