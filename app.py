import base64
import datetime
import io

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.exceptions import PreventUpdate

import requests
import pandas as pd
import utils
import charts
import plotly.graph_objs as go
from plotly.subplots import make_subplots

test_calibration_df = None
calibration_period = None


external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
)

server = app.server

app.layout = html.Div(
    children=[
        dcc.Tabs(
            id="main-tabs",
            value="upload-data-tab",
            vertical=False,
            children=[
                dcc.Tab(
                    value="upload-data-tab",
                    label="Upload data",
                    children=[
                        html.Hr(),
                        dcc.Upload(
                            id="upload-data",
                            children=html.Div(["Drag and Drop or ", html.A("Select Accelerations CSV")]),
                            style={
                                "width": "100%",
                                "height": "60px",
                                "lineHeight": "60px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "5px",
                                "textAlign": "center",
                                "margin": "0px",
                            },
                            # Allow multiple files to be uploaded
                            multiple=True,
                        ),
                    ],
                ),
                dcc.Tab(
                    value="acceleration-charts-tab",
                    label="Acceleration charts",
                    children=[
                        html.Hr(),
                        dcc.Loading(id="magnitude-chart-loading", type="circle", children=dcc.Graph(id="magnitude-graph")),
                        dcc.Loading(id="mhp-chart-loading", type="circle", children=dcc.Graph(id="mhp-graph")),
                    ],
                ),
                dcc.Tab(
                    value="dt-calibration-tab",
                    label="Remote DT calibration",
                    children=[
                        html.Hr(),
                        dcc.Loading(id="fig_with_rangeselector-loading", type="circle", children=dcc.Graph(id="fig_with_rangeselector")),
                        html.Div(id="output-container-range-slider"),
                        html.Button("Run MHPDT calibration", id="button-mhpdt-calibration"),
                        dcc.Loading(
                            id="mhpdt-calibration-loading",
                            type="circle",
                            children=html.Div(id="mhpdt-results-div"),
                            #     style={"position": "fixed", "top": "50%", "left": "50%"}
                        ),
                    ],
                ),
            ],
        ),
        dcc.Store(id="dataframe-json-storage"),
    ]
)


def parse_contents(contents, filename, date):
    # content_type, content_string = contents.split(',')
    _, content_string = contents.split(",")

    decoded = base64.b64decode(content_string)
    try:
        if "csv" in filename:

            df = utils.generate_basic_df(io.StringIO(decoded.decode("utf-8")))
            df = utils.add_features_to_df(df)
            global test_calibration_df
            test_calibration_df = df.copy()

        else:
            return html.Div(["The uploaded filetype can only be CSV."])

    except Exception as e:
        print(e)
        return html.Div(["There was an error processing this file."])

    df = df.reset_index(drop=False)
    json_data = df.to_dict("records")
    return json_data


@app.callback(
    Output("dataframe-json-storage", "data"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    State("upload-data", "last_modified"),
)
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [parse_contents(c, n, d) for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)]
        return children


@app.callback(Output("main-tabs", "value"), Input("dataframe-json-storage", "data"))
def init_tab_switch_on_upload(data):

    global test_calibration_df

    if test_calibration_df is None:
        raise PreventUpdate

    if test_calibration_df is not None:
        return "acceleration-charts-tab"


@app.callback(Output("magnitude-graph", "figure"), Input("dataframe-json-storage", "data"))
def update_magnitude_chart(json_data):

    if json_data is None:
        raise PreventUpdate

    df = pd.DataFrame.from_dict(json_data[0])
    df = df.set_index("timestamp")
    fig = charts.generate_chart(df, feature_name="magnitude")
    return fig


@app.callback(Output("mhp-graph", "figure"), Input("dataframe-json-storage", "data"))
def update_mhp_chart(json_data):

    if json_data is None:
        raise PreventUpdate

    df = pd.DataFrame.from_dict(json_data[0])
    df = df.set_index("timestamp")
    fig = charts.generate_chart(df, feature_name="mhp")
    return fig


@app.callback(Output("fig_with_rangeselector", "figure"), Input("dataframe-json-storage", "data"))
def update_mhp_chart(json_data):

    if json_data is None:
        raise PreventUpdate

    df = pd.DataFrame.from_dict(json_data[0])
    df = df.set_index("timestamp")
    fig = charts.generate_chart_with_rangeselector(df, feature_name="mhp")
    return fig


@app.callback(
    Output("output-container-range-slider", "children"),
    [Input("fig_with_rangeselector", "relayoutData")],
)
def update_slider_output_values(relayoutData):

    if relayoutData is None:
        raise PreventUpdate

    if test_calibration_df is None:
        return html.Div(children=None)

    global calibration_period

    calibration_period = slice(test_calibration_df.index[0], test_calibration_df.index[-1])

    # Handles case when user zooms on chart to select range:
    if "xaxis.range[0]" in relayoutData:
        new_range_data_start = relayoutData["xaxis.range[0]"]
        new_range_data_start = pd.to_datetime(new_range_data_start)

        new_range_data_stop = relayoutData["xaxis.range[1]"]
        new_range_data_stop = pd.to_datetime(new_range_data_stop)

        calibration_period = slice(new_range_data_start, new_range_data_stop)

    # Handles case when user zooms on rangeslider to select range:
    elif "xaxis.range" in relayoutData:
        new_range_data = relayoutData["xaxis.range"]
        calibration_period = slice(pd.to_datetime(new_range_data[0]), pd.to_datetime(new_range_data[1]))

    else:
        new_range_data = calibration_period

    diff = calibration_period.stop - calibration_period.start

    message_header = html.P("Selected calibration period:")
    message_list = html.Ul(
        id="calibration-period-list",
        children=[html.Li(f"range: [ {calibration_period.start} : {calibration_period.stop} ]"), html.Li(f"length of period:  {diff}")],
        style={"padding-left": "10px"},
    )

    return html.Div(children=[message_header, message_list])


@app.callback(
    Output(component_id="mhpdt-results-div", component_property="children"),
    [Input(component_id="button-mhpdt-calibration", component_property="n_clicks")],
)
def click_button_call_mhpdt_calibration(n_clicks):

    if n_clicks is None:
        raise PreventUpdate
    else:
        global test_calibration_df, calibration_period

        acceleration_data = test_calibration_df.copy().loc[calibration_period]
        calibration_json = utils.accelerations_csv_to_json(acceleration_data, json_attribute="downTimeCalibrationData", file_path=None)

        r = requests.post(
            "https://haris-oee-ml-azure-functions-staging.azurewebsites.net/api/MHPDT_cross_validation",
            headers={"Content-Type": "application/json"},
            json=calibration_json,
        )

        try:
            calibration_result = r.json()
        except ValueError:
            calibration_result = r.text

        str_result = str(calibration_result)
        return html.Div(str_result)


if __name__ == "__main__":
    app.run_server(debug=True)
