import base64
import io
import dash_html_components as html
import plotly.graph_objs as go

import pandas as pd
import numpy as np
from typing import List, Dict, Union
from sklearn.decomposition import PCA
import json
import logging

# change default plotly theme
import plotly.io

plotly.io.templates.default = "plotly_white"

logger = logging.getLogger(__name__)


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


def generate_basic_df(filepath: str) -> pd.DataFrame:
    """

    Parameters
    ----------
    filepath    filepath as string

    Returns     basic pd.DataFrame with timestamp as index
    -------

    """
    df = pd.read_csv(filepath, sep=",")
    df["timestamp"] = pd.to_datetime(df.timestamp, format="%Y-%m-%dT%H:%M:%S.%f")
    df = df.set_index("timestamp")

    if not df.index.is_monotonic_increasing:
        print("Warning: Dataframe DatetimeIndex is not monotonically increasing.")

    return df


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
    logger.setLevel(logging.INFO)
    logger.info(f"using parameters mhp_window_size: {mhp_window_size} and alpha: {alpha}")

    df["magnitude"] = np.sqrt(df.x ** 2 + df.y ** 2 + df.z ** 2)
    df["mhp"] = magnitude_highpass(df, window_size=mhp_window_size)
    df["no_gravity"] = gravity_free_magnitude(df, alpha=alpha)
    df["pca"] = PCA(n_components=1).fit_transform(df[["x", "y", "z"]].fillna(0))

    # add rolling averages
    for axis in ["x", "y", "z"]:
        df[f"{axis}_{mhp_window_size}_avg"] = df[axis].rolling(mhp_window_size).mean().fillna(0)

    return df


def df_to_json_accelerations(df: pd.DataFrame, timestamp_as_string=False) -> List[Dict[str, Union[str, Dict[str, float]]]]:
    """
    reproduces input identical to what GM consumes. useful for testing haris-oee-ml module prediction methods
    """
    accelerations = []

    for row in df[["x", "y", "z"]].iterrows():
        if timestamp_as_string:
            timestamp = row[0].strftime("%Y-%m-%dT%H:%M:%S.%f")
        else:
            timestamp = row[0]

        temp_dict = {"timestamp": timestamp, "acceleration": {"x": row[1][0], "y": row[1][1], "z": row[1][2]}}
        accelerations += [temp_dict]
    return accelerations


def andon_state_list_generator(states_array: pd.Series) -> List:
    """

    Parameters
    ----------
    states_array

    Returns
    -------

    """
    state_list = states_array[states_array != states_array.shift(1)].to_frame()
    state_list.index = state_list.index.astype(str)
    state_list = list(state_list.itertuples(index=True, name=None))

    return state_list


def accelerometer_denoising(df: pd.DataFrame, cols=("x", "y", "z"), win_size=3, denoising_method="mean") -> pd.DataFrame:
    """

    Parameters
    ----------
    df
    cols
    win_size
    denoising_method

    Returns
    -------

    """

    df_denoised = df.copy()

    for col in cols:
        col_name = f"{col}"
        if "median" == denoising_method:
            df_denoised[col_name] = df_denoised[col].rolling(window=win_size).median().values
        elif "mean" == denoising_method:
            df_denoised[col_name] = df_denoised[col].rolling(window=win_size).mean().values
        else:
            raise AttributeError("Invalid ct denoising filter type. 'denoising_method' = 'median' or 'mean'")

    return df_denoised


def load_json_mobile_calibration_data(calibration_file_path: str) -> pd.DataFrame:
    """

    Parameters
    ----------
    calibration_file_path   file path to json file containing calibration file.

    Returns                 pd.DataFrame containing x,y,z acceleration values and the state tags of
                            the calibration process.
    -------

    Loads calibration data from json into dataframe.

    """

    with open(calibration_file_path, "r") as json_file:
        survey_settings = json.loads(json_file.read())

    # access calibration dataframe:
    calibration_data = survey_settings["surveyRun"]["surveyRunDetail"]
    calibration_data = calibration_data["machineCalibrationData"]["machineCalibrationDataLogs"]

    # iterate over beacon log entries:
    calibration_data_list = []
    for data in calibration_data:
        array_to_append = [data["beaconLog"]["mappedAdvertising"]["time"]]
        array_to_append += [data["beaconLog"]["mappedAdvertising"]["accelerometerX"]]
        array_to_append += [data["beaconLog"]["mappedAdvertising"]["accelerometerY"]]
        array_to_append += [data["beaconLog"]["mappedAdvertising"]["accelerometerZ"]]
        array_to_append += [data["state"]]

        calibration_data_list += [array_to_append]

    # create dataframe:
    column_names = ["timestamp", "x", "y", "z", "state"]
    df = pd.DataFrame(calibration_data_list, columns=column_names)
    df["timestamp"] = pd.to_datetime(df.timestamp, format="%Y-%m-%dT%H:%M:%S.%f")
    df = df.set_index(keys="timestamp")

    return df


def str_date_converter(row):
    date_str = str(row).split()
    return date_str[0] + "T" + date_str[1][:-3]


def virtual_gateway_dummy_data(df_input, out_filepath):
    df = df_input.copy()
    df["timestamp"] = df.index.to_series().apply(str_date_converter)
    df = df.set_index("timestamp")
    df.to_csv(out_filepath, sep=",", header=True, index=True)


def downtime_calibration_to_df(calibration_data_json):
    df_temp = pd.DataFrame(calibration_data_json)
    # df['ts'] = df.ts.str.split(':').apply(lambda x: x[:-1]).str.join('')
    df_temp["timestamp"] = pd.to_datetime(df_temp.timestamp, format="%Y-%m-%dT%H:%M:%S.%f")

    df = pd.DataFrame(list(df_temp.acceleration.values), index=df_temp.timestamp)
    df["state"] = df_temp.state.values

    return df


def rolling_std_feature(df, window_size="3s"):

    rolling_std = df[["x", "y", "z"]].rolling(window_size).std(ddof=1).fillna(0)
    # pca_feature = PCA(n_components=1).fit_transform(rolling_std)

    feature = np.sum(np.power(rolling_std, 3), axis=1)

    return feature


def accelerations_csv_to_json(df: pd.DataFrame, json_attribute="cycleTimeCalibrationData", file_path=None):

    calibration_json = {json_attribute: []}
    for row in df[["x", "y", "z"]].iterrows():
        try:
            ts = row[0].strftime("%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            ts = row[0].strftime("%Y-%m-%dT%H:%M:%S.0")
        x, y, z = row[1][0], row[1][1], row[1][2]

        json_element = {"timestamp": ts, "acceleration": {"x": x, "y": y, "z": z}}
        calibration_json[json_attribute].append(json_element)

    if file_path:
        with open(file_path, "w") as f:
            json.dump(calibration_json, f, sort_keys=True, indent=2, separators=(",", ": "))
    else:
        return calibration_json


def load_df_from_local_storage(json_data):

    df = pd.DataFrame.from_dict(json_data[0])
    df["timestamp"] = pd.to_datetime(df.timestamp)
    df = df.set_index("timestamp")

    return df


def load_calibration_period_from_local_storage(json_data) -> slice:
    range_start = pd.to_datetime(json_data["start"])
    range_stop = pd.to_datetime(json_data["stop"])
    return slice(range_start, range_stop)


def parse_contents(contents, filename, date):
    # content_type, content_string = contents.split(',')
    _, content_string = contents.split(",")

    decoded = base64.b64decode(content_string)
    try:
        if "csv" in filename:

            df = generate_basic_df(io.StringIO(decoded.decode("utf-8")))
            df = add_features_to_df(df)

        else:
            return html.Div(["The uploaded filetype can only be CSV."])

    except Exception as e:
        print(e)
        return html.Div(["There was an error processing this file."])

    df = df.reset_index(drop=False)
    json_data = df.to_dict("records")
    return json_data


def calculate_calibration_period_based_on_user_action(df: pd.DataFrame, relayoutData: dict, calibration_period: dict) -> dict:

    # Handles case when user zooms/pans on chart to select range:
    if "xaxis.range[0]" in relayoutData:

        new_range_start = relayoutData["xaxis.range[0]"]
        new_range_stop = relayoutData["xaxis.range[1]"]

        calibration_period = {"start": new_range_start, "stop": new_range_stop}

    # Handles case when user zooms on rangeslider to select range:
    elif "xaxis.range" in relayoutData:

        new_range_start = relayoutData["xaxis.range"][0]
        new_range_stop = relayoutData["xaxis.range"][1]
        calibration_period = {"start": new_range_start, "stop": new_range_stop}

    # Handles case when user switches tabs
    elif "autosize" in relayoutData:
        # if chart data is unchanged init calibration period, otherwise leave unchanged:
        if calibration_period is None:
            new_range_start = df.index[0].strftime(format="%Y-%m-%dT%H:%M:%S.%f")
            new_range_stop = df.index[-1].strftime(format="%Y-%m-%dT%H:%M:%S.%f")
            calibration_period = {"start": new_range_start, "stop": new_range_stop}

    # Two more relayoutdata cases :
    # - when user clicks on 'all': relayoutData={'xaxis.autorange':True}
    # - when user clicks on 'house' icon: relayoutData={'xaxis.autorange':True,'xaxis.showspikes':False} --> this sometimes gets stuck
    # in these cases default to the whole range of the data:
    else:
        new_range_start = df.index[0].strftime(format="%Y-%m-%dT%H:%M:%S.%f")
        new_range_stop = df.index[-1].strftime(format="%Y-%m-%dT%H:%M:%S.%f")
        calibration_period = {"start": new_range_start, "stop": new_range_stop}

    return calibration_period


def date_format_sanity_checker(df: pd.DataFrame, start_date_str: str, end_date_str: str) -> str:

    fail_error_msg = None

    try:
        start_date = pd.to_datetime(start_date_str, format="%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        logger.error("Invalid start date format")
        fail_error_msg = "Invalid start date format. Unable to filter date range."
    try:
        end_date = pd.to_datetime(end_date_str, format="%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        logger.error("Invalid end date format")
        fail_error_msg = "Invalid end date format. Unable to filter date range."

    return fail_error_msg


def date_range_sanity_checker(df: pd.DataFrame, start_date_str: str, end_date_str: str) -> str:

    fail_error_msg = None
    start_date = pd.to_datetime(start_date_str, format="%Y-%m-%dT%H:%M:%S.%f")
    end_date = pd.to_datetime(end_date_str, format="%Y-%m-%dT%H:%M:%S.%f")

    if start_date:
        if (df.index[0] > start_date) or (df.index[-1] < start_date):
            fail_error_msg = "Given start date is out of timeseries' range"
    if end_date:
        if (df.index[-1] < end_date) or (df.index[0] > end_date):
            fail_error_msg = "Given end date is out of timeseries' range"

    return fail_error_msg


def filter_chart_on_daterange(fig, df, start_date_str: str, end_date_str: str) -> str:

    fail_error_msg = None
    start_date = pd.to_datetime(start_date_str, format="%Y-%m-%dT%H:%M:%S.%f")
    end_date = pd.to_datetime(end_date_str, format="%Y-%m-%dT%H:%M:%S.%f")

    if (start_date is None) and (end_date is None):
        fail_error_msg = "Start date and end date are equal. Unable to filter date range."

    if (start_date is None) or (start_date_str == ""):
        start_date = df.index[0]
    if (end_date is None) or (end_date_str == ""):
        end_date = df.index[-1]

    if start_date == end_date:
        fail_error_msg = "Start date and end date are equal. Unable to filter date range."

    if start_date > end_date:
        fail_error_msg = "Start date is greater than end date. Unable to filter date range."

    if fail_error_msg is None:
        fig["layout"]["xaxis"]["range"][0] = start_date.strftime(format="%Y-%m-%dT%H:%M:%S.%f")
        fig["layout"]["xaxis"]["range"][1] = end_date.strftime(format="%Y-%m-%dT%H:%M:%S.%f")
        fig["layout"]["xaxis"]["autorange"] = False

    return fail_error_msg
