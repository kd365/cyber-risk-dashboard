import dash_html_components as html
import dash_core_components as dcc

def create_layout(app):
    return html.Div([
        html.H1("Cybersecurity Risk Dashboard"),
        dcc.Dropdown(id="firm-selector", options=[], placeholder="Select a firm"),
        dcc.Graph(id="risk-indicator-graph"),
        dcc.Graph(id="sentiment-timeline"),
    ])
