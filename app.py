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
import plotly.graph_objs as go
from plotly.subplots import make_subplots

test_calibration_df = None


def generate_chart(df: pd.DataFrame, feature_name: str) -> go.Figure:

    fig = go.Figure()
    fig.add_scatter(x=df.index, y=df[feature_name], name=feature_name, showlegend=True)
    fig.update_layout(title=f"Acceleration's {feature_name} feature chart")
    return fig


external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    update_title="Loading...",
    suppress_callback_exceptions=True,
)

server = app.server

app.layout = html.Div(
    [
        dcc.Upload(
            id="upload-data",
            children=html.Div(["Drag and Drop or ", html.A("Select Files")]),
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
        # html.Div(id='output-data-upload'),
        dcc.Loading(
            id="loading-1",
            type="circle",
            style={"position": "fixed", "top": "50%", "left": "50%"},
            children=html.Div(id="output-data-upload"),
        ),
    ]
)


def parse_contents(contents, filename, date):
    # content_type, content_string = contents.split(',')
    _, content_string = contents.split(",")

    decoded = base64.b64decode(content_string)
    try:
        if "csv" in filename:
            # # Assume that the user uploaded a CSV file
            # df = pd.read_csv(
            #     io.StringIO(decoded.decode('utf-8')))
            df = utils.generate_basic_df(io.StringIO(decoded.decode("utf-8")))
            df = utils.add_features_to_df(df)
            global test_calibration_df
            test_calibration_df = df.copy().loc[
                "2021-05-07 11:10:00":"2021-05-07 11:13:00"
            ]

            fig_magnitude = generate_chart(df, feature_name="magnitude")
            fig_mhp = generate_chart(df, feature_name="mhp")
            df = df.reset_index(drop=False)

        elif "xls" in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
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
                            html.Button(
                                "Run MHPDT calibration", id="button-mhpdt-calibration"
                            ),
                            html.Div(id="mhpdt-results-div"),
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
        children = [
            parse_contents(c, n, d)
            for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)
        ]
        return children


@app.callback(
    Output(component_id="mhpdt-results-div", component_property="children"),
    [Input(component_id="button-mhpdt-calibration", component_property="n_clicks")],
)
def click_button_call_mhpdt_calibration(n_clicks):

    global test_calibration_df
    calibration_json = utils.accelerations_csv_to_json(
        test_calibration_df, json_attribute="downTimeCalibrationData", file_path=None
    )

    if n_clicks is None:
        raise PreventUpdate
    else:
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
