import numpy as np
import pandas as pd
import skopt
from skopt import gp_minimize
import utils
import micro_filter
import sklearn.metrics
from typing import Dict

def fast_MHPDT(df, feature_to_use='mhp', threshold=0.1, andon_uptime_threshold=5):
    df_results = df.copy()
    df_results['is_cycle'] = np.where(df_results[feature_to_use] >= threshold, 1, 0)

    return df_results

def andon_state_from_mhpdt(df, andon_threshold=pd.to_timedelta('30s')):
    if 'is_cycle' not in df.columns:
        return list()

    df['timestamp'] = df.index
    run_list = df.to_dict('records')
    andon_prediction_list = list()

    andon_state = np.zeros_like(df['is_cycle'].values)
    last_csp = df.index[0] - andon_threshold

    for i, item in enumerate(run_list):
        if i > 0:
            if not item['is_cycle']:
                if last_csp + andon_threshold < item['timestamp']:
                    andon_state[i] = 0
                else:
                    andon_state[i] = 1
            else:
                andon_state[i] = 1
                last_csp = item['timestamp']

    return andon_state

def andon_prediction_with_filtering(df, params):
    prediction_df = fast_MHPDT(df,
                               feature_to_use='mhp',
                               threshold=params['model_params']['mhp_threshold'],
                               andon_uptime_threshold=params['model_params']['andon_uptime_threshold']
                               )

    # ANDON:
    andon_threshold = pd.Timedelta(seconds=params['model_params']["andon_uptime_threshold"])
    andon_state_from_mhpdt_array = andon_state_from_mhpdt(prediction_df.copy(), andon_threshold=andon_threshold)

    prediction_df['state'] = andon_state_from_mhpdt_array
    up_filter_size = str(params['model_params']["up_filter_size"]) + 's'
    down_filter_size = str(params['model_params']["down_filter_size"]) + 's'
    prediction_df = micro_filter.filtering(prediction_df, andon_flag='state', up_filter_size=up_filter_size,
                              down_filter_size=down_filter_size, first_filter='down')

    return prediction_df

def hmm_tagged_mhpdt_score(df,
                           ground_truth,
                           feature_threshold=15,
                           up_filter_size=2,
                           down_filter_size=2):
    params = {
        "model_type": "MHPDT",
        "model_params": {
            "mhp_threshold": feature_threshold,
            "min_cycle_time": 0,
            "andon_uptime_threshold": 5, 
            "up_filter_size": up_filter_size,
            "down_filter_size": down_filter_size
        }
    }

    prediction_df = andon_prediction_with_filtering(df, params)

    difference = ground_truth - prediction_df['state_filtered']
    score = np.sum(np.abs(difference))

    return score

def run_optimization(df_input, labels):
    np.random.seed(314156)

    def f(x):
        score = hmm_tagged_mhpdt_score(df_input,
                                       labels,
                                       feature_threshold=x[0],
                                       up_filter_size=x[1],
                                       down_filter_size=x[2])

        return score

    space = [skopt.space.Real(0.1, 4, name='mhp_threshold'),
             skopt.space.Integer(0, 120, name='up_filter_size'),
             skopt.space.Integer(0, 120, name='down_filter_size')]

    res = gp_minimize(f, space, n_calls=50, random_state=314156)
    return res

def optimization_score(df: pd.DataFrame, params: Dict, tagged_labels: pd.Series) -> float:
    
    prediction_df = andon_prediction_with_filtering(df, params)
    predicted_labels = prediction_df.state_filtered

    score = sklearn.metrics.accuracy_score(tagged_labels,predicted_labels)

    return round(score,3)