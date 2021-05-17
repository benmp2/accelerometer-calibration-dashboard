import logging
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
import utils


def hmm_based_andon_tag(df, feature_name):
    obs_seq = np.array(df[[feature_name]])

    ghmm = GaussianHMM(
        n_components=2,
        covariance_type="diag",
        min_covar=1e-3,
        algorithm="viterbi",
        random_state=1,
        n_iter=100,
        tol=1e-3,
        params="stmc",
        init_params="stmc",
    )

    ghmm.fit(obs_seq)

    # transition reset
    trans = 1e-50  # 1e-300
    ghmm.transmat_ = np.array([[1 - trans, trans], [trans, 1 - trans]])
    logprob, state_seq = ghmm.decode(obs_seq)
    return logprob, state_seq


def generate_tagged_data(df):
    logprob, state_seq = hmm_based_andon_tag(df, feature_name="mhp")
    tagged_states = pd.Series(state_seq, index=df.index)
    tagged_states = utils.std_based_state_flipping(df.mhp, tagged_states)

    return tagged_states
