__author__ = "Nicolas Gutierrez"

# Standard libraries
import os
# Third party libraries
import pandas as pd
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import numpy as np
# Custom libraries
from utilities.utilities import load_yaml
from datahandling.postgresqlinterface import PostGreSqlInterface
from datahandling.dataextractor import DataExtractor
from ping.pingdevicetype import PingDeviceType
from ping.pingfunctions import calculate_stats, calculate_histogram, calculate_downtime
from power.powerdevicetype import PowerDeviceType
from layout.ping_tab import ping_tab
from layout.power_tab import power_tab

# User configuration
configuration_path = os.path.join("config", "config.yaml")

# Style
pd.options.plotting.backend = "plotly"
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Code Configuration
configuration = load_yaml(configuration_path)

# Querier
querier = PostGreSqlInterface(configuration["postgresql"])

# Initialization ping
sensor_type = "ping"
ping_data_extractor = DataExtractor(sensor_type, configuration[sensor_type], querier)

# Initialization energy
sensor_type = "power"
power_data_extractor = DataExtractor(sensor_type, configuration[sensor_type], querier)

# Dash layout
app = Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div(style={'backgroundColor': '#111111'},
                      children=[
                          html.H1(children="House Dashboard",
                                  style={'textAlign': 'center',
                                         'color': '#FFFFFF'}),
                          dcc.Tabs([
                              ping_tab,
                              power_tab
                          ])
                      ])


@app.callback(
    Output(component_id='device_ping_distribution_graph', component_property='figure'),
    Input(component_id='interval_refresh_ping_slow', component_property="n_intervals")
)
def stream_fig_internet(value):
    # Retrieve data
    sensor_name = "google"
    dfs_dict = ping_data_extractor.retrieve_sensors_data([sensor_name], 24)
    list_of_histogram_pds = calculate_histogram(dfs_dict)
    fig = go.Figure()
    # Plot
    for (values, bins) in list_of_histogram_pds:
        bins_average = np.average(np.diff(bins))
        fig.add_trace(go.Bar(x=bins[:-1]-bins_average/2, y=values, name=sensor_name))
    fig.update_layout(
        xaxis_title="Ping [ms]",
        yaxis_title="Number of values",
        template="plotly_dark",
        margin=dict(t=5, b=5),
    )
    return fig


@app.callback(
    Output(component_id='downtime_led', component_property='value'),
    Input(component_id='interval_refresh_ping_slow', component_property="n_intervals")
)
def update_led(value):
    # Retrieve data
    sensor_name = "google"
    dfs_dict = ping_data_extractor.retrieve_sensors_data([sensor_name], 24)
    list_of_downtime = calculate_downtime(dfs_dict)
    return np.around(list_of_downtime[0], 1)


# Callbacks
@app.callback(
    Output(component_id='infrastructure_graph', component_property='figure'),
    Input(component_id='interval_refresh_ping', component_property="n_intervals")
)
def stream_fig_network(value):
    # Retrieve data
    dfs_dict = ping_data_extractor.retrieve_type_data(
        [PingDeviceType.INFRASTRUCTURE],
        configuration["hours_to_display"])
    fig = go.Figure()
    # Plot
    for df_index, df_name in enumerate(dfs_dict):
        fig.add_trace(go.Scatter(x=dfs_dict[df_name].index, y=dfs_dict[df_name]["value"],
                                 name=df_name))
    fig.update_layout(
        xaxis_title="Date and Time",
        yaxis_title="Ping [ms]",
        template="plotly_dark",
        margin=dict(t=5, b=5),
        yaxis={"rangemode": "nonnegative"}
    )
    return fig


@app.callback(
    Output(component_id='personal_devices_table', component_property='data'),
    Input(component_id='interval_refresh_ping', component_property="n_intervals")
)
def stream_table(value):
    dict_of_dfs = ping_data_extractor.retrieve_type_data(
        [PingDeviceType.PERSONAL_DEVICE],
        configuration["hours_for_tables"])
    table = calculate_stats(dict_of_dfs)

    return table.to_dict('records')


@app.callback(
    Output(component_id='power_graph', component_property='figure'),
    Input(component_id='interval_refresh_power', component_property="n_intervals")
)
def stream_fig_power(value):
    # Retrieve data
    dfs_dict = power_data_extractor.retrieve_type_data(
        [PowerDeviceType.PLUG],
        configuration["hours_to_display"])
    fig = go.Figure()
    # Plot
    for df_index, df_name in enumerate(dfs_dict):
        fig.add_trace(go.Scatter(x=dfs_dict[df_name].index, y=dfs_dict[df_name]["value"],
                                 name=df_name))
    fig.update_layout(
        xaxis_title="Date and Time",
        yaxis_title="Power [W]",
        template="plotly_dark",
        margin=dict(t=5, b=5),
        yaxis={"rangemode": "nonnegative"}
    )
    return fig


# @app.callback(
#     Output(component_id='output-container-button', component_property='children'),
#     [Input(component_id='button-example-1', component_property='n_clicks')],
#     )
# def update_output(n_clicks):
#     if n_clicks is not None:
#         if n_clicks % 2 == 0:
#             switch_off_function("192.168.0.49")
#         else:
#             switch_on_function("192.168.0.49")
#
#     return 'The button has been clicked {} times'.format(
#         n_clicks
#     )

app.run_server(host="0.0.0.0", port=8069, dev_tools_ui=True,  # debug=True,
               dev_tools_hot_reload=True, threaded=True)
