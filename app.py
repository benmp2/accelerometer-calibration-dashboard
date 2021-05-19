import json
import logging, sys
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
from dash.exceptions import PreventUpdate

import requests
import pandas as pd
import dash_utils
import charts
import plotly.graph_objs as go
from plotly.subplots import make_subplots

import components.app_layout as layout

logger = logging.getLogger(__name__)

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
                layout.tab_upload(),
                layout.tab_acceleration_charts(),
                layout.tab_mhpdt_calibration(),
            ],
        ),
        dcc.Store(id="dataframe-json-storage"),
        dcc.Store(id="mhpdt-calibration-period-storage"),
        dcc.Store(id="mhpdt-calibration-param-storage"),
    ]
)


@app.callback(
    Output("dataframe-json-storage", "data"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    State("upload-data", "last_modified"),
)
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [dash_utils.parse_contents(c, n, d) for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)]
        return children


@app.callback(Output("main-tabs", "value"), Input("dataframe-json-storage", "data"))
def init_tab_switch_on_upload(data):

    if data is None:
        raise PreventUpdate

    if data is not None:
        return "acceleration-charts-tab"


@app.callback(Output("mag-mhp-subplot-graph", "figure"), Input("dataframe-json-storage", "data"))
def update_mhp_chart(json_data):

    if json_data is None:
        raise PreventUpdate

    df = dash_utils.load_df_from_local_storage(json_data)
    fig = charts.generate_subplots_chart(df)

    return fig


@app.callback(
    [
        Output(component_id="fig_with_rangeselector", component_property="figure"),
        Output(component_id="fig_with_rangeselector", component_property="relayoutData"),
        Output(component_id="incorrect-filter-range-div", component_property="children"),
    ],
    [
        Input(component_id="dataframe-json-storage", component_property="data"),
        Input(component_id="calibration-date-filter-button", component_property="n_clicks"),
        State(component_id="calibration-filter-start-date", component_property="value"),
        State(component_id="calibration-filter-end-date", component_property="value"),
        State(component_id="fig_with_rangeselector", component_property="figure"),
    ],
)
def update_rangeselector_chart(json_data, n_clicks, start_date_str, end_date_str, fig):

    if json_data is None:
        raise PreventUpdate

    df = dash_utils.load_df_from_local_storage(json_data)

    fail_div_msg = None
    relayoutData = None

    if (n_clicks is not None) and (fig is not None):
        # TODO: this should be refactored:
        # - make sure input dates are in the correct format
        # - date filtering is within allowed range
        # - if all clear select specified range
        # - trigger relayoutData by specifying new range with "xaxis.range"

        fail_div_msg = dash_utils.date_format_sanity_checker(df, start_date_str, end_date_str)

        if fail_div_msg is None:
            fail_div_msg = dash_utils.date_range_sanity_checker(df, start_date_str, end_date_str)

        if fail_div_msg is None:
            fail_div_msg = dash_utils.filter_chart_on_daterange(fig, df, start_date_str, end_date_str)

        if fail_div_msg is None:
            if start_date_str == "" or start_date_str is None:
                start_date_str = df.index[0].strftime(format="%Y-%m-%dT%H:%M:%S.%f")
            if end_date_str == "" or end_date_str is None:
                end_date_str = df.index[-1].strftime(format="%Y-%m-%dT%H:%M:%S.%f")

            relayoutData = {"xaxis.range": [start_date_str, end_date_str]}
    else:
        fig = charts.generate_chart_with_rangeselector(df, feature_name="mhp")

    return fig, relayoutData, fail_div_msg


@app.callback(
    [
        Output(component_id="output-container-range-slider", component_property="children"),
        Output(component_id="mhpdt-calibration-period-storage", component_property="data"),
    ],
    [
        Input(component_id="fig_with_rangeselector", component_property="relayoutData"),
        Input(component_id="dataframe-json-storage", component_property="data"),
        State(component_id="mhpdt-calibration-period-storage", component_property="data"),
    ],
)
def update_slider_output_values(relayoutData, json_data, calibration_period):

    if relayoutData is None:
        raise PreventUpdate

    if json_data is None:
        raise PreventUpdate

    df = dash_utils.load_df_from_local_storage(json_data)
    calibration_period = dash_utils.calculate_calibration_period_based_on_user_action(df, relayoutData, calibration_period)
    diff = pd.to_datetime(calibration_period["stop"]) - pd.to_datetime(calibration_period["start"])

    message_header = html.P("Selected calibration period:")
    message_list = html.Ul(
        id="calibration-period-list",
        children=[
            html.Li(f"range: [ {calibration_period['start']} : {calibration_period['stop']} ]"),
            html.Li(f"length of period:  {diff}"),
        ],
        style={"padding-left": "20px"},
    )

    output_message_div = html.Div(children=[message_header, message_list], style={"margin-left": "80px"})

    return output_message_div, calibration_period


@app.callback(
    Output(component_id="mhpdt-results-div", component_property="children"),
    [
        Input(component_id="button-mhpdt-calibration", component_property="n_clicks"),
        State(component_id="dataframe-json-storage", component_property="data"),
        State(component_id="mhpdt-calibration-period-storage", component_property="data"),
    ],
)
def click_button_call_mhpdt_calibration(n_clicks, json_data, calibration_period_json):

    if n_clicks is None:
        raise PreventUpdate

    if json_data is None:
        raise PreventUpdate

    calibration_period = dash_utils.load_calibration_period_from_local_storage(calibration_period_json)
    df = dash_utils.load_df_from_local_storage(json_data)

    acceleration_data = df.copy().loc[calibration_period].round(3)
    calibration_json = dash_utils.accelerations_csv_to_json(acceleration_data, json_attribute="downTimeCalibrationData", file_path=None)

    azure_func_url = os.environ.get("AZURE_FUNC_URL", "http://localhost:7071")

    try:
        r = requests.post(
            f"{azure_func_url}/api/MHPDT_cross_validation",
            headers={"Content-Type": "application/json"},
            json=calibration_json,
        )
    except requests.exceptions.RequestException as e:
        calibration_result = "Unable to connect to server hosting azure functions."
        r = None

    if r:
        try:
            calibration_result = r.json()
        except ValueError:
            calibration_result = r.text

    str_result = str(calibration_result)
    return html.Div(str_result, style={"margin-left": "80px"})


@app.callback(
    Output("mhpdt-calibration-param-storage", "data"),
    Input(component_id="mhpdt-results-div", component_property="children"),
)
def store_mhpdt_calibration_parameters(input_data):
    if input_data is None:
        raise PreventUpdate

    return input_data["props"]


@app.callback(
    Output(component_id="dt-calibration-graph", component_property="figure"),
    [
        Input(component_id="mhpdt-calibration-param-storage", component_property="data"),
        State(component_id="dataframe-json-storage", component_property="data"),
        State(component_id="mhpdt-calibration-period-storage", component_property="data"),
    ],
)
def plot_mhpdt_calibration_results(calibration_params, json_data, calibration_period_json):

    if calibration_params is None:
        raise PreventUpdate

    calibration_period = dash_utils.load_calibration_period_from_local_storage(calibration_period_json)

    df = dash_utils.load_df_from_local_storage(json_data)
    df_calibration = df.copy().loc[calibration_period].round(3)

    if "calibration_score" in calibration_params["children"]:

        # convert calibration params:
        params_json_format = calibration_params["children"].replace("'", '"')
        params = json.loads(params_json_format)
        # generate figure
        fig = charts.generate_mhpdt_calibration_chart(df_calibration, params)

        return fig
    else:
        return go.Figure()


@app.callback(
    Output(component_id="apply-mhpdt-calibration-to-all-graph", component_property="figure"),
    [
        Input(component_id="button-apply-mhpdt-calibration-to-all", component_property="n_clicks"),
        State(component_id="dataframe-json-storage", component_property="data"),
        State(component_id="mhpdt-calibration-param-storage", component_property="data"),
    ],
)
def plot_mhpdt_calibration_applied_to_whole_period(n_clicks, df_json_data, calibration_params):

    if n_clicks is None:
        raise PreventUpdate

    if calibration_params is None:
        raise PreventUpdate

    df = dash_utils.load_df_from_local_storage(df_json_data)
    df_calibration = df.copy().round(3)

    if "calibration_score" in calibration_params["children"]:

        # convert calibration params:
        params_json_format = calibration_params["children"].replace("'", '"')
        params = json.loads(params_json_format)
        # generate figure
        fig = charts.generate_mhpdt_calibration_chart(df_calibration, params)

        return fig
    else:
        return go.Figure()


@app.callback(
    Output(component_id="pandas-eval-chart", component_property="figure"),
    [
        Input(component_id="pandas-eval-button", component_property="n_clicks"),
        State(component_id="dataframe-json-storage", component_property="data"),
        State(component_id="pandas-eval-input", component_property="value"),
    ],
)
def update_evaluate_chart(n_clicks, json_data, eval_expression):

    if n_clicks is None:
        raise PreventUpdate
    elif json_data is None:
        raise PreventUpdate
    else:
        df = dash_utils.load_df_from_local_storage(json_data).round(3)
        df_plot = None
        try:
            df_plot = df.eval(eval_expression, inplace=False)
        except AttributeError:
            logger.info("invalid expression")
        except ValueError:
            logger.info("unable to calculate expression")

        if df_plot is not None:
            fig = go.Figure()
            fig.add_scatter(x=df_plot.index, y=df_plot.values, name=df_plot.name, showlegend=True)
            fig.update_layout(title=f"Acceleration's feature chart from '{eval_expression}' evaluated expression")
        else:
            fig = go.Figure()

        return fig


if __name__ == "__main__":

    import os

    logging.basicConfig(
        format="[%(asctime)s %(levelname)s] %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger()
    level_name = logging.getLevelName(logger.getEffectiveLevel())
    logger.info(f"Starting Haris-MHPDT-calibration-dashboard at log level {level_name}")

    debug = False if os.environ.get("DASH_DEBUG_MODE", None) == "False" else True
    dash_host = os.environ.get("DASH_HOST", "127.0.0.1")
    dash_port = os.environ.get("DASH_PORT", 8050)

    app.run_server(debug=debug, host=dash_host, port=int(dash_port))
