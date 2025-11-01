from flask import Flask
import dash
from dashboard.layout import build_layout
from dashboard.callbacks import register_callbacks


server = Flask(__name__) 
app = dash.Dash(__name__, server=server, suppress_callback_exceptions=True)
app.title = "Cybersecurity Risk Dashboard"
app.layout = build_layout()
register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
