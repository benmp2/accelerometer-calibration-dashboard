import os, sys
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

dir_path = os.path.dirname(os.path.realpath("./MHPDT_cross_validation/*"))
sys.path.insert(0, dir_path)
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
    calibration_score = round(calibration_score * 100, 3)
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


def generate_custom_mhpdt_chart(fig, df, params, n_clicks, add_feature_data=True):

    df_transient = utils.add_features_to_df(df[["x", "y", "z"]].copy().round(3), mhp_window_size="6s")
    df_transient_dropped = utils.drop_transient_mhp_window_sized_data(df_transient, mhp_window_size="6s")

    df_plot = mhpdt_cv.andon_prediction_with_filtering(df_transient_dropped, params)

    if add_feature_data:
        fig.add_scatter(x=df_plot.index, y=df_plot.mhp, name="mhp")

    legend = f"filtered mhpdt andon model #{int(n_clicks)}"
    fig.add_scatter(x=df_plot.index, y=df_plot.state_filtered, mode="lines", name=legend)

    return fig
