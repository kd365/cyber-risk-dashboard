from dash import html, dcc
import pandas as pd
import boto3
import io

def get_company_options():
    s3 = boto3.client("s3")
    bucket = "cyber-risk-artifacts"
    key = "data/reference/cybersecurity_tickers.csv"

    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        df = pd.read_csv(io.BytesIO(obj["Body"].read()))
        print("Loaded tickers:", df.head())
        return [{"label": f"{row['name']} ({row['ticker']})", "value": row["ticker"]} for _, row in df.iterrows()]
    except Exception as e:
        print(f"Error loading tickers from s3: {e}")
        return []

def build_layout():
    return html.Div([
        html.H1("Cybersecurity Risk Dashboard"),

        html.P("Explore risk signals from SEC filings and earnings call transcripts for cybersecurity companies. "
               "Start by entering your name and selecting a company to analyze."),

        html.Hr(),

        # User Info Section
        html.Div([
            html.H3("1. Identify Yourself"),
            html.P("Your name and email are used to personalize the ingestion process. Required for SEC filings."),
            html.Label("Your Name"),
            dcc.Input(id="user-name", type="text", placeholder="Enter your name", style={"width": "50%"}),
            html.Br(), html.Br(),
            html.Label("Your Email"),
            dcc.Input(id="user-email", type="email", placeholder="Enter your email", style={"width": "50%"})
        ], style={"marginBottom": "30px"}),

        html.Hr(),

        # Company Selection
        html.Div([
            html.H3("2. Choose a Cybersecurity Company"),
            html.P("Select a company to analyze. This will drive the risk indicators and visualizations below."),
            dcc.Dropdown(
                id="company-dropdown",
                options=get_company_options(),
                value="CRWD",  # Default selection
                searchable=True,
                placeholder="Select or search for a company...",
                style={"width": "60%"}
            )
        ], style={"marginBottom": "30px"}),

        html.Hr(),

        # Ingestion Type Selection
        html.Div([
            html.H3("3. Select Data Sources to Ingest"),
            html.P("Choose one or both data types to ingest for the selected company."),
            dcc.Checklist(
                id="ingestion-type",
                options=[
                    {"label": "SEC Filings", "value": "sec"},
                    {"label": "Transcripts", "value": "transcripts"}
                ],
                value=[],
                labelStyle={"display": "inline-block", "marginRight": "20px"}
            )
        ], style={"marginBottom": "30px"}),

        html.Hr(),

        # Ingestion Trigger
        html.Div([
            html.H3("4. Start Ingestion"),
            html.Button("Start Ingestion", id="start-ingestion", n_clicks=0, disabled=True),
            html.Button("Reset Status", id="reset-status", n_clicks=0)
            html.Div(id="ingestion-status", style={"marginTop": "10px", "fontWeight": "bold"})
        ], style={"marginBottom": "30px"}),

        # Progress Display with Loading Spinner
        dcc.Interval(id="progress-poller", interval=3000, n_intervals=0),
        dcc.Loading(
            id="loading-bar",
            type="default",
            children=html.Div(id="progress-display"),
            fullscreen=False
        ),

        html.Hr(),

        # Visualizations
        html.Div([
            html.H3("5. Risk Indicator Trends"),
            html.Div(id="plot-1"),
            html.Div(id="plot-2"),
            html.Div(id="sentiment-comparison"),
            html.Div(id="wordcloud-container"),
            html.Div(id="risk-indicators"),
            html.Div(id="artifact-table")
        ]),

        # Optional refresh interval for dashboard updates
        dcc.Interval(id="refresh-interval", interval=60000, n_intervals=0)
    ], style={"padding": "40px"})
