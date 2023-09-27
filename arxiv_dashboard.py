# Import packages
from dash import Dash, html, dash_table
import pandas as pd
import numpy as np

import plotly.express as ex

# Incorporate data
df = pd.read_csv("arxiv-analysis/arxiv_sample.csv")

# Initialize the app
app = Dash(__name__)

# App layout
app.layout = html.Div([
    html.Div(children='arXiv Analysis Dashboard'),
    dash_table.DataTable(data=df.to_dict('records'), page_size=10)
])

# Run the app
if __name__ == '__main__':
    app.run(debug=True)


