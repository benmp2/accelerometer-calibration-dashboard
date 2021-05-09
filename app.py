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
    [
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
        html.Div(id="output-data-upload"),
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

            fig_magnitude = charts.generate_chart(df, feature_name="magnitude")
            fig_mhp = charts.generate_chart(df, feature_name="mhp")
            fig_mhp_rangeselector = charts.generate_chart_with_rangeselector(df, feature_name="mhp")

        else:
            return html.Div(["The uploaded filetype can only be CSV."])

    except Exception as e:
        print(e)
        return html.Div(["There was an error processing this file."])

    return html.Div(
        [
            html.Hr(),
            dcc.Tabs(
                [
                    dcc.Tab(
                        label="Charts",
                        children=[
                            html.Hr(),
                            dcc.Graph(figure=fig_magnitude),
                            dcc.Graph(figure=fig_mhp),
                        ],
                    ),
                    dcc.Tab(
                        label="Remote calibration",
                        children=[
                            dcc.Graph(
                                id="fig_with_rangeselector",
                                figure=fig_mhp_rangeselector,
                            ),
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
                    dcc.Tab(
                        label="Input data",
                        children=[
                            html.Hr(),
                            dash_table.DataTable(
                                data=df.head(5).to_dict("records"),
                                columns=[{"name": i, "id": i} for i in df.columns],
                                editable=True,
                            ),
                        ],
                    ),
                ]
            ),
        ]
    )


@app.callback(
    Output("output-data-upload", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    State("upload-data", "last_modified"),
)
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [parse_contents(c, n, d) for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)]
        return children


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
        # TODO: make sure selected period is the same as the calibration period sent to azure!
        print(f"running mhpdt for: [{acceleration_data.index[0]},{acceleration_data.index[-1]}]")
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


@app.callback(
    Output("output-container-range-slider", "children"),
    [Input("fig_with_rangeselector", "relayoutData")],
)
def update_slider_output_values(relayoutData):

    global calibration_period

    calibration_period = slice(test_calibration_df.index[0], test_calibration_df.index[-1])
    if relayoutData:
        new_range_data = relayoutData.get("xaxis.range", calibration_period)
        if new_range_data != calibration_period:
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


if __name__ == "__main__":
    app.run_server(debug=True)
