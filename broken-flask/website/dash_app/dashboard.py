from .. import app

import os

from dash import Dash, html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import datapackage
import numpy as np
import pandas as pd
import pickle
import plotly.express as px
import plotly.graph_objects as go

# Create the dash app
app_dash = Dash(
    # Set the current module name
    __name__, server = app, url_base_pathname='/dash/',
    # Include the bootstrap CSS stylesheet
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    # Include meta tags in the HTML head
    meta_tags=[
        # Set the viewport width to the device width and initial scale to 1
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        
    ],
    suppress_callback_exceptions= True
)



###########################################
########### LOAD DATA #############

# URL of the data package on datahub.io
data_url = 'https://datahub.io/core/oil-prices/datapackage.json'
# Name of the cache file to store the dataframes
cache_filename = 'oil_prices_dataframes.pkl'

# Check if the cache file exists
if os.path.exists(cache_filename):
    # If the cache file exists, load the dataframes from the cache file
    with open(cache_filename, 'rb') as f:
        # Use the pickle library to load the dataframes from the binary file
        dataframes = pickle.load(f)
else:
    # If the cache file does not exist, load the data from the source and save it to the cache file
    # Load the data package using the datapackage library
    package = datapackage.Package(data_url)
    # Get the resources in the data package
    resources = package.resources
    # Create an empty dictionary to store the dataframes
    dataframes = {}
    # Loop through each resource in the data package
    for resource in resources:
        # Check if the resource is tabular (i.e. it contains data in a table)
        if resource.tabular:
            # Read the data from the CSV file
            data = pd.read_csv(resource.descriptor['path'])
            # Store the data in the dataframes dictionary
            dataframes[resource.name] = data
    # Save the dataframes to the cache file
    with open(cache_filename, 'wb') as f:
        # Use the pickle library to save the dataframes to a binary file
        pickle.dump(dataframes, f)
###########################################


# create a dropdown menu to select the chart to display
chart_selector = dcc.Dropdown(
    id='chart-selector',
    options=[
        {'label': 'Daily Brent', 'value': 'brent-daily_csv'},
        {'label': 'Weekly Brent', 'value': 'brent-week_csv'},
        {'label': 'Monthly Brent', 'value': 'brent-month_csv'},
        {'label': 'Yearly Brent', 'value': 'brent-year_csv'},
        {'label': 'Daily WTI', 'value': 'wti-daily_csv'},
        {'label': 'Weekly WTI', 'value': 'wti-week_csv'},
        {'label': 'Monthly WTI', 'value': 'wti-month_csv'},
        {'label': 'Yearly WTI', 'value': 'wti-year_csv'},
    ],
    value='brent-daily_csv'
)

# Add Checkboxes so user can include the moving average they want to see.
MA_selection = dcc.Checklist(
        id='ma-tickboxes',
        options=[
            {'label': 'SMA20', 'value': 'SMA20'},
            {'label': 'SMA50', 'value': 'SMA50'},
            {'label': 'SMA100', 'value': 'SMA100'}
            
        ],
        value=[]
    )

# Create another dropdown so user can see the histogram of returns over a given period.
period_selection = dcc.Dropdown(
        id='period-selection',
        options=[
            {'label': '20 Periods', 'value': '20'},
            {'label': '50 Periods', 'value': '60'},
            {'label': '100 Periods', 'value': '100'},
            {'label': '250 Periods', 'value': '250'}
        ],
        value='100'
    )

###### SELECT AND EDIT DATA ######
# Callback function to get the data
@app_dash.callback(
    # Output component to update with the data
    Output('data-output', 'data'),
    # Input component used to trigger the update
    [Input('chart-selector', 'value')]
)
def get_data(selected_chart):
    # Loop through the dataframes
    for chart_name, data in dataframes.items():
        # Check if the selected chart name matches the current chart name
        if chart_name == selected_chart:
            # Return the data as output
            data["SMA20"] = data["Price"].rolling(20).mean()
            data["SMA50"] = data["Price"].rolling(50).mean()
            data["SMA100"] = data["Price"].rolling(100).mean()
            data["STD20"] = data["Price"].rolling(20).std()
            data["STD50"] = data["Price"].rolling(50).std()
            data["STD100"] = data["Price"].rolling(100).std()
            data["Returns"] = data["Price"].pct_change() 
            data = data.to_dict()
            return data
#############################


######## LINE CHART ########
@app_dash.callback(
    # Output component to update with the plot
    Output('line-chart', 'figure'),
    # Input component used to trigger the update
    [Input('data-output', 'data')], Input('ma-tickboxes', 'value')
)
def update_line_chart(data, ma_selections):
    # Call the function to plot the line chart using the returned data
    return plot_line_chart(data, ma_selections)

# Function to plot the line chart
def plot_line_chart(data, ma_selections):
    # Create a line chart using plotly express
    data = pd.DataFrame.from_dict(data)
    figure = px.line(data, x='Date', y='Price', labels={'x': 'Date', 'y': 'Price'}) 
    # Update the chart layout to have a transparent background
    figure.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)', 'paper_bgcolor': 'rgba(0, 0, 0, 0)'})
    # Update the x-axis of the chart to have a fixed range and include a slider
    figure.update_xaxes(fixedrange = True, nticks =14, rangeslider_visible=True)
    for ma in ma_selections:
        figure.add_scatter(x=data['Date'], y=data[ma], mode = 'lines', name = ma)
    
    return figure


######## HISTOGRAM ########

#Create a callback function which produces a histogram of the returns of a given period for the chosen chart.
@app_dash.callback(
    Output('returns-hist', 'figure'),
    [Input('data-output', 'data')], Input('period-selection', 'value')
)
def update_histogram(data, period_selections):
    data = pd.DataFrame.from_dict(data)
    data = data.tail(int(period_selections))
    figure = px.histogram(data, x="Returns", nbins = 15, title = f"Returns over the last {period_selections} periods")
    figure.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)', 'paper_bgcolor': 'rgba(0, 0, 0, 0)'})
    return figure


######## GAUGE ########
@app_dash.callback(
    # Output component to update with the plot
    Output('100-gauge-chart', 'figure'),
    # Input component used to trigger the update
    [Input('data-output', 'data')]
)
def plot_100_gauge(data):
    data = pd.DataFrame.from_dict(data)
    plot_bgcolor = "#ffffff"
    section_colors = [plot_bgcolor,  "#ff6961", "#fffaa0","lightgreen"] 
    section_text = ["", "<b>Over Bought</b>", "<b>Neutral</b>",  "<b>Over Sold</b>"]
    num_sections = len(section_colors) - 1

    filter = data.iloc[-1]
    current_value = filter["Price"]  #data["Price"].loc["2008-04-07"]
    current_date = filter["Date"] #data["Date"].iloc[-3750]
    sma100 = filter.SMA100 #data["SMA100"].iloc[-3750]
    std100 = filter.STD100
    #std100 = data["Price"].rolling(100).std().iloc[-1]
    min_value = sma100 - (2 * std100)
    max_value = sma100 + (2 * std100)
    pointer_length = np.sqrt(2) / 4
        
    if current_value <= min_value:
        pointer_angle = np.pi
    elif current_value >= max_value:
        pointer_angle = 0
    else:
        pointer_angle = np.pi * (1 - (max(min_value, min(max_value, current_value)) - min_value) / (max_value - min_value))

    fig = go.Figure(
                data=[
                    go.Pie(
                        values=[0.5] + (np.ones(num_sections) / 2 / num_sections).tolist(),
                        rotation=90,
                        hole=0.5,
                        marker_colors=section_colors,
                        text=section_text,
                        textinfo="text",
                        hoverinfo="skip",
                    ),
                ],
                layout=go.Layout(
                    showlegend=False,
                    margin=dict(b=0,t=10,l=10,r=10),
                    width=450,
                    height=450,
                    paper_bgcolor=plot_bgcolor,
                    annotations=[
                        go.layout.Annotation(
                            text=f"<b>Current Date:</b><br>{current_date}<br>Current Price:</b><br>{current_value}",
                            x=0.5, xanchor="center", xref="paper",
                            y=0.25, yanchor="bottom", yref="paper",
                            showarrow=False,
                        )
                    ],
                    shapes=[
                        go.layout.Shape(
                            type="circle",
                            x0=0.48, x1=0.52,
                            y0=0.48, y1=0.52,
                            fillcolor="#333",
                            line_color="#333",
                        ),
                        go.layout.Shape(
                            type="line",
                            x0=0.5, x1=0.5 + pointer_length * np.cos(pointer_angle),
                            y0=0.5, y1=0.5 + pointer_length * np.sin(pointer_angle),
                            line=dict(color="#333", width=4)
                        )
                    ]
                )
            )
    return fig



@app_dash.callback(
    # Output component to update with the plot
    Output('50-gauge-chart', 'figure'),
    # Input component used to trigger the update
    [Input('data-output', 'data')]
)
def plot_50_gauge(data):
    data = pd.DataFrame.from_dict(data)
    plot_bgcolor = "#ffffff"
    section_colors = [plot_bgcolor,  "#ff6961", "#fffaa0","lightgreen"] 
    section_text = ["", "<b>Over Bought</b>", "<b>Neutral</b>",  "<b>Over Sold</b>"]
    num_sections = len(section_colors) - 1

    filter = data.iloc[-1]
    current_value = filter["Price"]  #data["Price"].loc["2008-04-07"]
    current_date = filter["Date"] #data["Date"].iloc[-3750]
    sma50 = filter.SMA50 #data["SMA50"].iloc[-3750]
    std50 = filter.STD50
    #std50 = data["Price"].rolling(50).std().iloc[-1]
    min_value = sma50 - (2 * std50)
    max_value = sma50 + (2 * std50)
    pointer_length = np.sqrt(2) / 4
        
    if current_value <= min_value:
        pointer_angle = np.pi
    elif current_value >= max_value:
        pointer_angle = 0
    else:
        pointer_angle = np.pi * (1 - (max(min_value, min(max_value, current_value)) - min_value) / (max_value - min_value))

    fig = go.Figure(
                data=[
                    go.Pie(
                        values=[0.5] + (np.ones(num_sections) / 2 / num_sections).tolist(),
                        rotation=90,
                        hole=0.5,
                        marker_colors=section_colors,
                        text=section_text,
                        textinfo="text",
                        hoverinfo="skip",
                    ),
                ],
                layout=go.Layout(
                    showlegend=False,
                    margin=dict(b=0,t=10,l=10,r=10),
                    width=450,
                    height=450,
                    paper_bgcolor=plot_bgcolor,
                    annotations=[
                        go.layout.Annotation(
                            text=f"<b>Current Date:</b><br>{current_date}<br>Current Price:</b><br>{current_value}",
                            x=0.5, xanchor="center", xref="paper",
                            y=0.25, yanchor="bottom", yref="paper",
                            showarrow=False,
                        )
                    ],
                    shapes=[
                        go.layout.Shape(
                            type="circle",
                            x0=0.48, x1=0.52,
                            y0=0.48, y1=0.52,
                            fillcolor="#333",
                            line_color="#333",
                        ),
                        go.layout.Shape(
                            type="line",
                            x0=0.5, x1=0.5 + pointer_length * np.cos(pointer_angle),
                            y0=0.5, y1=0.5 + pointer_length * np.sin(pointer_angle),
                            line=dict(color="#333", width=4)
                        )
                    ]
                )
            )
    return fig

@app_dash.callback(
    # Output component to update with the plot
    Output('20-gauge-chart', 'figure'),
    # Input component used to trigger the update
    [Input('data-output', 'data')]
)
def plot_20_gauge(data):
    data = pd.DataFrame.from_dict(data)
    plot_bgcolor = "#ffffff"
    section_colors = [plot_bgcolor,  "#ff6961", "#fffaa0","lightgreen"] 
    section_text = ["", "<b>Over Bought</b>", "<b>Neutral</b>",  "<b>Over Sold</b>"]
    num_sections = len(section_colors) - 1

    filter = data.iloc[-1]
    current_value = filter["Price"]  #data["Price"].loc["2008-04-07"]
    current_date = filter["Date"] #data["Date"].iloc[-3750]
    sma20 = filter.SMA20 #data["SMA20"].iloc[-3750]
    std20 = filter.STD20
    #std20 = data["Price"].rolling(20).std().iloc[-1]
    min_value = sma20 - (2 * std20)
    max_value = sma20 + (2 * std20)
    pointer_length = np.sqrt(2) / 4
        
    if current_value <= min_value:
        pointer_angle = np.pi
    elif current_value >= max_value:
        pointer_angle = 0
    else:
        pointer_angle = np.pi * (1 - (max(min_value, min(max_value, current_value)) - min_value) / (max_value - min_value))

    fig = go.Figure(
                data=[
                    go.Pie(
                        values=[0.5] + (np.ones(num_sections) / 2 / num_sections).tolist(),
                        rotation=90,
                        hole=0.5,
                        marker_colors=section_colors,
                        text=section_text,
                        textinfo="text",
                        hoverinfo="skip",
                    ),
                ],
                layout=go.Layout(
                    showlegend=False,
                    margin=dict(b=0,t=10,l=10,r=10),
                    width=450,
                    height=450,
                    paper_bgcolor=plot_bgcolor,
                    annotations=[
                        go.layout.Annotation(
                            text=f"<b>Current Date:</b><br>{current_date}<br>Current Price:</b><br>{current_value}",
                            x=0.5, xanchor="center", xref="paper",
                            y=0.25, yanchor="bottom", yref="paper",
                            showarrow=False,
                        )
                    ],
                    shapes=[
                        go.layout.Shape(
                            type="circle",
                            x0=0.48, x1=0.52,
                            y0=0.48, y1=0.52,
                            fillcolor="#333",
                            line_color="#333",
                        ),
                        go.layout.Shape(
                            type="line",
                            x0=0.5, x1=0.5 + pointer_length * np.cos(pointer_angle),
                            y0=0.5, y1=0.5 + pointer_length * np.sin(pointer_angle),
                            line=dict(color="#333", width=4)
                        )
                    ]
                )
            )
    return fig



# create the layout for the app
app_layout = html.Div(
    className='container',
    children=[
        html.H1('Oil Prices'),
        chart_selector,
        dcc.Store(id='data-output'),
        MA_selection,
        dcc.Graph(id='line-chart',
        config={'modeBarButtonsToAdd':['drawline','drawopenpath','drawclosedpath','drawcircle','drawrect',  'eraseshape'  ],
        'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian']},
        hoverData={'points': [{'customdata': '2020-01-01'}]}
        ),
        period_selection,
        dcc.Graph(id = 'returns-hist'),
        html.Div(
        style={'display': 'flex'},
        children=[
            html.Div(
                style={'width': '33%', 'display': 'inline-block'},
                children=[
                    html.H2("20 period Overbought/Oversold indicator"),
                    dcc.Graph(id = '20-gauge-chart')
                ]
            ),
            html.Div(
                style={'width': '33%', 'display': 'inline-block'},
                children=[
                    html.H2("50 period Overbought/Oversold indicator"),
                    dcc.Graph(id = '50-gauge-chart')
                ]
            ),
            html.Div(
                style={'width': '33%', 'display': 'inline-block'},
                children=[
                    html.H2("100 period Overbought/Oversold indicator"),
                    dcc.Graph(id = '100-gauge-chart')
                ]
            ),
        ]
    )

    ]
)

def init_dash(server):
    app_dash = Dash(server=server, routes_pathname_prefix="/dash/")
    app_dash.layout = app_layout
    return app_dash.server

if __name__ == '__main__':
    app_dash.run_server(debug=True)