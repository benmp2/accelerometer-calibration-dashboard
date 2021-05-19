import dash_core_components as dcc
import dash_html_components as html


def tab_upload() -> dcc.Tab:

    tab = dcc.Tab(
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
    )

    return tab


def tab_acceleration_charts() -> dcc.Tab:

    tab = dcc.Tab(
        value="acceleration-charts-tab",
        label="Acceleration charts",
        children=[
            html.Hr(),
            dcc.Loading(id="mhp-chart-loading", type="circle", children=dcc.Graph(id="mag-mhp-subplot-graph")),
            html.Hr(),
            html.Div(
                id="pandas-eval-div",
                children=[
                    dcc.Input(
                        id="pandas-eval-input",
                        type="text",
                        placeholder="Specify expression to evaluate",
                        debounce=True,
                        style={"width": "500px", "margin-right": "30px", "margin-left": "80px"},
                    ),
                    html.Button(id="pandas-eval-button", children="Evaluate"),
                ],
            ),
            dcc.Loading(id="pandas-eval-chart-loading", type="circle", children=dcc.Graph(id="pandas-eval-chart")),
        ],
    )
    return tab


def tab_mhpdt_calibration() -> dcc.Tab:
    tab = dcc.Tab(
        value="dt-calibration-tab",
        label="MHPDT calibration",
        children=[
            html.Hr(),
            dcc.Loading(id="fig_with_rangeselector-loading", type="circle", children=dcc.Graph(id="fig_with_rangeselector")),
            html.Div(id="output-container-range-slider"),
            html.Div(
                id="calibration-filter-div",
                children=[
                    html.Hr(),
                    div_calibration_filter_input(),
                    html.Button(id="calibration-date-filter-button", children="Apply date filter"),
                    html.Div(id="calibration-filter-success"),
                ],
                style={"margin-left": "80px"},
            ),
            html.Hr(),
            html.Button("Run MHPDT calibration", id="button-mhpdt-calibration", style={"margin-left": "80px", "margin-bottom": "10px"}),
            dcc.Loading(
                id="mhpdt-calibration-loading",
                type="circle",
                children=[html.Div(id="mhpdt-results-div"), dcc.Graph(id="dt-calibration-graph")],
            ),
            html.Hr(),
            html.Button(
                "Apply MHPDT calibration to whole period",
                id="button-apply-mhpdt-calibration-to-all",
                style={"margin-left": "80px"},
            ),
            dcc.Loading(
                id="mhpdt-calibration-to-all-loading",
                type="circle",
                children=[
                    html.Div(id="apply-mhpdt-calibration-to-all-div"),
                    dcc.Graph(id="apply-mhpdt-calibration-to-all-graph"),
                ],
            ),
            html.Hr(),
            div_custom_model(),
        ],
    )

    return tab


def div_calibration_filter_input() -> html.Div:
    div = html.Div(
        id="calibration-filter-inputs",
        children=[
            dcc.Input(
                id="calibration-filter-start-date",
                placeholder="Start date (format: 2021-05-10 07:26:15.631)",
                style={"width": "400px", "margin-right": "10px"},
            ),
            dcc.Input(
                id="calibration-filter-end-date",
                placeholder="End date (format: 2021-05-10 07:41:20.631)",
                style={"width": "400px"},
            ),
            html.Div(id="incorrect-filter-range-div"),
        ],
        style={"margin-bottom": "10px"},
    )
    return div


def div_custom_model() -> html.Div:
    div = html.Div(
        id="custom-mhpdt-model-input-div",
        children=[
            details_custom_model_param(),
            html.Div(
                [
                    html.Button(
                        id="load-calibration-params-to-mhpdt-custom-model-button",
                        children="Load calibration parameters",
                        style={"display": "inline-block"},
                    ),
                    html.Button(
                        id="reset-mhpdt-custom-model-default-params-button",
                        children="Reset to default model",
                        style={"margin-left": "20px", "display": "inline-block"},
                    ),
                ],
                style={"margin-top": "10px", "margin-left": "80px"},
            ),
            html.Div(
                [
                    html.Button(
                        id="plot-custom-mhpdt-model-button",
                        children="Plot custom MHPDT model",
                        style={"display": "inline-block"},
                    ),
                    dcc.Checklist(
                        options=[
                            {"label": "Add to existing chart", "value": "add-to-chart"},
                        ],
                        value=["add-to-chart"],
                        style={"margin-left": "20px", "display": "inline-block"},
                    ),
                    html.Button(
                        id="clear-mhpdt-custom-model-chart-button",
                        children="Clear chart",
                        style={"margin-left": "20px", "display": "inline-block"},
                    ),
                ],
                style={"margin-top": "10px", "margin-left": "80px"},
            ),
            html.Div(id="custom-mhpdt-error-div"),
            dcc.Loading(
                id="mhpdt-custom_model-loading",
                type="circle",
                children=[html.Div(id="mhpdt-applied-parameters-div"), dcc.Graph(id="mhpdt-custom-model-graph")],
            ),
        ],
    )
    return div


def details_custom_model_param() -> html.Details:
    details = html.Details(
        id="mhpdt-custom-model-params-details",
        open=True,
        children=[
            html.Summary(
                id="custom-mhpdt-model-details-summary",
                children=dcc.Markdown("##### MHPDT model parameters", style={"display": "inline-block"}),
            ),
            html.Div(
                id="mhpdt-threshold-div",
                children=[
                    html.Div(
                        id="mhpdt-threshold-text-div",
                        children=dcc.Markdown("* **Threshold** - `range: [0.0, 15.0]`"),
                        style={"display": "inline-block", "margin-right": "20px"},
                    ),
                    dcc.Input(
                        id="mhpdt-threshold-input",
                        type="number",
                        min=0,
                        max=15,
                        value=0.1,
                        style={
                            "width": "150px",
                            "display": "inline-block",
                            "margin-right": "20px",
                            "float": "right",
                        },
                    ),
                ],
                style={"margin-bottom": "20px", "width": "35%"},
            ),
            html.Div(
                id="mhpdt-min-cycle-time-div",
                children=[
                    html.Div(
                        id="mhpdt-min-cycle-time-text-div",
                        children=dcc.Markdown("* **Min-cycle-time** \[sec\] - `range: [0, 100]`"),
                        style={"display": "inline-block", "margin-right": "20px"},
                    ),
                    dcc.Input(
                        id="mhpdt-min-cycle-time-input",
                        type="number",
                        min=0,
                        max=100,
                        step=1,
                        value=0,
                        style={
                            "width": "150px",
                            "display": "inline-block",
                            "margin-right": "20px",
                            "float": "right",
                        },
                    ),
                ],
                style={"margin-bottom": "20px", "width": "35%"},
            ),
            html.Div(
                id="mhpdt-andon-uptime-threshold-div",
                children=[
                    html.Div(
                        id="mhpdt-andon-uptime-threshold-text-div",
                        children=dcc.Markdown("* **Andon uptime** \[sec\] - `range: [0, 100]`"),
                        style={"display": "inline-block", "margin-right": "20px"},
                    ),
                    dcc.Input(
                        id="mhpdt-andon-uptime-threshold-input",
                        type="number",
                        min=0,
                        max=100,
                        step=1,
                        value=5,
                        style={
                            "width": "150px",
                            "display": "inline-block",
                            "margin-right": "20px",
                            "float": "right",
                        },
                    ),
                ],
                style={"margin-bottom": "20px", "width": "35%"},
            ),
            html.Div(
                id="mhpdt-uptime-filter-div",
                children=[
                    html.Div(
                        id="mhpdt-uptime-filter-text-div",
                        children=dcc.Markdown("* **Uptime filter** \[sec\] - `range: [0, 120]`"),
                        style={"display": "inline-block", "margin-right": "20px"},
                    ),
                    dcc.Input(
                        id="mhpdt-uptime-filter-input",
                        type="number",
                        min=0,
                        max=120,
                        step=1,
                        value=0,
                        style={
                            "width": "150px",
                            "display": "inline-block",
                            "margin-right": "20px",
                            "float": "right",
                        },
                    ),
                ],
                style={"margin-bottom": "20px", "width": "35%"},
            ),
            html.Div(
                id="mhpdt-downtime-filter-div",
                children=[
                    html.Div(
                        id="mhpdt-downtime-filter-text-div",
                        children=dcc.Markdown("* **Downtime filter** \[sec\] - `range: [0, 120]`"),
                        style={"display": "inline-block", "margin-right": "20px"},
                    ),
                    dcc.Input(
                        id="mhpdt-downtime-filter-input",
                        type="number",
                        min=0,
                        max=120,
                        step=1,
                        value=0,
                        style={
                            "width": "150px",
                            "display": "inline-block",
                            "margin-right": "20px",
                            "float": "right",
                        },
                    ),
                ],
                style={"margin-bottom": "20px", "width": "35%"},
            ),
            html.Div(
                id="mhpdt-filter-order-div",
                children=[
                    html.Div(
                        [
                            html.Div(
                                id="mhpdt-filter-order-text-div",
                                children=dcc.Markdown("* **Filtering order**"),
                                style={"display": "inline-block", "margin-right": "20px"},
                            ),
                            dcc.RadioItems(
                                id="mhpdt-filter-order-radioitems",
                                options=[
                                    {"label": "Down", "value": "down"},
                                    {"label": "Up", "value": "up"},
                                ],
                                value="down",
                                style={"margin-left": "20px"},
                            ),
                        ],
                        style={"display": "inline-block"},
                    ),
                    html.Div(
                        [
                            html.Div(
                                id="mhpdt-period-to-use-text-div",
                                children=dcc.Markdown("* **Period to use**"),
                                style={"display": "inline-block", "margin-right": "20px"},
                            ),
                            dcc.RadioItems(
                                id="mhpdt-period-to-use-radioitems",
                                options=[
                                    {"label": "Whole period", "value": "full"},
                                    {"label": "Calibration period", "value": "calibration"},
                                ],
                                value="full",
                                style={"margin-left": "20px"},
                            ),
                        ],
                        style={"display": "inline-block"},
                    ),
                ],
                style={"margin-bottom": "20px", "width": "35%"},
            ),
        ],
        style={"margin-left": "80px"},
    )

    return details
