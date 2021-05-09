import pandas as pd
import plotly.graph_objs as go

def generate_chart(df: pd.DataFrame, feature_name: str) -> go.Figure:

    fig = go.Figure()
    fig.add_scatter(x=df.index, y=df[feature_name], name=feature_name, showlegend=True)
    fig.update_layout(title=f"Acceleration's {feature_name} feature chart")
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