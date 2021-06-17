import numpy as np
import pandas as pd
import logging
from typing import Tuple, List, Dict


def generate_basic_df(accelerations: List[Dict]) -> pd.DataFrame:
    """

    Parameters
    ----------
    filepath    filepath as string

    Returns     basic pd.DataFrame with timestamp as index
    -------

    """

    df_temp = pd.DataFrame(accelerations)
    if not type(df_temp.index) is pd.DatetimeIndex:
        df_temp.timestamp = pd.to_datetime(df_temp.timestamp, format="%Y-%m-%dT%H:%M:%S.%f")

    df = pd.DataFrame(df_temp.acceleration.values.tolist(), index=df_temp.timestamp)

    # if not df.index.is_monotonic_increasing:
    #     logging.warning('Dataframe DatetimeIndex is not monotonically increasing.')

    return df


def magnitude_highpass(df: pd.DataFrame, axes: List = ["x", "y", "z"], window_size: str = "3s") -> np.array:
    """

    Parameters
    ----------
    df              input pd.Dataframe
    axes            axes to include in magnitude highpass calculation
    window_size     size of rolling window, e.g. 3 or '3s'

    Returns         np.array of magnitude highpass values
    -------

    """

    mhp = df[axes].values - df[axes].rolling(window=window_size).mean().values
    # magnitude calculation:
    mhp = np.sqrt(np.sum(np.power(mhp, 2), axis=1))

    return mhp


def linear_acceleration(data_array: np.array, alpha: float = 0.8) -> np.array:
    """

    Parameters
    ----------
    data_array
    alpha

    Returns
    -------

    """

    gravity = np.ones_like(data_array) * data_array.values[0]
    for i in range(data_array.size)[1:]:
        # gravity can be considered as the low passed version of
        # the signal (using exponential smoothing):
        gravity[i] = alpha * gravity[i - 1] + (1 - alpha) * data_array[i]

    gravity = pd.Series(gravity, index=data_array.index)

    gravity_free_acceleration = data_array - gravity

    return gravity_free_acceleration


def gravity_free_magnitude(df: pd.DataFrame, alpha: float = 0.8):
    """

    Parameters
    ----------
    df
    alpha

    Returns
    -------

    """

    df_gravity_free = df[["x", "y", "z"]].copy()
    for axis in ["x", "y", "z"]:
        df_gravity_free[axis] = linear_acceleration(df_gravity_free[axis].copy(), alpha=alpha)
    magnitude = np.sqrt(df_gravity_free.pow(2).sum(axis=1))

    return magnitude


def add_features_to_df(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """

    Parameters
    ----------
    df

    Returns
    -------

    """

    alpha = kwargs.get("alpha", 0.8)
    mhp_window_size = kwargs.get("mhp_window_size", "3s")
    mhp_axis = kwargs.get("mhp_axis", ["x", "y", "z"])

    logging.info(f"using parameters mhp_window_size: {mhp_window_size}, mhp_axis: {mhp_axis} and alpha: {alpha} ")

    df["magnitude"] = np.sqrt(df.x ** 2 + df.y ** 2 + df.z ** 2)
    df["mhp"] = magnitude_highpass(df, window_size=mhp_window_size, axes=mhp_axis)
    df["no_gravity"] = gravity_free_magnitude(df, alpha=alpha)

    return df


def std_based_state_flipping(feature_series, state_series):
    flipped_states = np.zeros(state_series.size)

    state_A_mask = state_series.values == 0
    state_B_mask = state_series.values == 1

    state_A_std = feature_series[state_A_mask].std()
    state_B_std = feature_series[state_B_mask].std()

    if state_A_std >= state_B_std:
        flipped_states[state_A_mask] = 1
        flipped_states[state_B_mask] = 0
    else:
        flipped_states[state_A_mask] = 0
        flipped_states[state_B_mask] = 1

    if not np.array_equal(flipped_states, state_series):
        logging.info(f"flipping states! - state_A_std: {state_A_std} state_B_std: {state_B_std}")

    return pd.Series(flipped_states, index=state_series.index)


def drop_transient_mhp_window_sized_data(df: pd.DataFrame, mhp_window_size: str = "6s") -> pd.DataFrame:

    start_point = df.index[0]
    offset = pd.Timedelta(mhp_window_size)
    start_point = start_point + offset
    df = df.loc[start_point:]

    return df


def mean_based_state_ranking(feature_series, state_series):

    ranked_states = np.zeros(state_series.size)
    states = pd.unique(state_series)
    state_means = []

    # calculate each decode state's mean
    for state in states:
        mask = state_series.values == state
        state_mean = feature_series[mask].mean()
        state_means += [state_mean]

    sorted_state_means = np.argsort(state_means)

    # relabel data:
    for i, state in enumerate(states):
        mask = state_series.values == state
        ranked_states[mask] = np.where(sorted_state_means == i)[0]

    if not np.array_equal(ranked_states, state_series):
        logging.info(f"modifying state labels based on mean feature values!")

    ranked_state_series = pd.Series(ranked_states, index=state_series.index)

    return ranked_state_series
