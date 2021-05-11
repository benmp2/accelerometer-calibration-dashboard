import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

import os, sys
sys.path.append(os.path.abspath("C:\\Users\\benmp\\Work\\haris-oee-ml-azure-functions\\MHPDT_cross_validation"))
import utils
import micro_filter
import hmm_tagging
import mhpdt_cross_validation as mhpdt_cv


def generate_chart(df: pd.DataFrame, feature_name: str) -> go.Figure:

    fig = go.Figure()
    fig.add_scatter(x=df.index, y=df[feature_name], name=feature_name, showlegend=True)
    fig.update_layout(title=f"Acceleration's {feature_name} feature chart")
    return fig


def generate_subplots_chart(df: pd.DataFrame, feature_names: str = ("magnitude", "mhp")) -> go.Figure:

    row_count = len(feature_names)
    fig = make_subplots(
        rows=row_count,
        cols=1,
        shared_xaxes="columns",
        specs=[
            [{"type": "scatter"}],
            [{"type": "scatter"}],
        ],
        subplot_titles=[f"Acceleration's {f} feature chart" for f in feature_names],
    )

    for i, col in enumerate(feature_names, start=1):
        if col in df.columns:
            fig.add_scatter(x=df.index, y=df[col], name=col, showlegend=True, row=i, col=1)

    return fig


def generate_chart_with_rangeselector(df: pd.DataFrame, feature_name: str) -> go.Figure:

    # Create figure
    fig = go.Figure()

    fig.add_scatter(x=df.index, y=df[feature_name], name=feature_name)

    # Set title
    fig.update_layout(title_text="Select calibration period:")

    # Add range slider
    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list(
                    [
                        dict(step="all"),
                    ]
                )
            ),
            rangeslider=dict(visible=True),
            type="date",
        )
    )
    return fig


def generate_mhpdt_calibration_chart(df_calibration, params):

    df_calibration_transient = utils.add_features_to_df(df_calibration[["x", "y", "z"]].copy().round(3), mhp_window_size="6s")
    df_calibration_transient_dropped = utils.drop_transient_mhp_window_sized_data(df_calibration_transient, mhp_window_size="6s")

    tagged_states = hmm_tagging.generate_tagged_data(df_calibration_transient_dropped)
    prediction_df = mhpdt_cv.andon_prediction_with_filtering(df_calibration_transient_dropped, params)

    calibration_score = mhpdt_cv.optimization_score(df_calibration_transient_dropped, params, tagged_states)
    calibration_score = round(calibration_score*100, 3)
    print(f"{calibration_score}")

    fig = go.Figure()
    fig.add_scatter(x=prediction_df.index, y=prediction_df.mhp, name="mhp")
    fig.add_scatter(x=tagged_states.index, y=tagged_states, mode="lines", name="tagged sequence")

    # For 3 state hmm labeling:
    # tagged_states = hmm_tagging.relabel_active_states(tagged_states)
    # fig.add_scatter(x=tagged_states.index,y=tagged_states,mode='lines',name='tagged sequence relabeled')

    fig.add_scatter(
        x=prediction_df.index, y=prediction_df.state_filtered, mode="lines", line=dict(dash="dash"), name="mhpdt andon_states filtered"
    )

    fig.update_layout(title_text=f"MHPDT calibration result - accuracy score: {calibration_score} %")

    return fig
