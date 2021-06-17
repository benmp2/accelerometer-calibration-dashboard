import logging
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
import utils
from typing import List


def bic_general(likelihood_fn, k, X):
    """
    likelihood_fn: Function. Should take as input X and give out   the log likelihood
              of the data under the fitted model.
       k - int. Number of parameters in the model. The parameter that we are trying to optimize.
                For HMM it is number of states.
                For GMM the number of components.
       X - array. Data that been fitted upon.
    source:
        https://en.wikipedia.org/wiki/Bayesian_information_criterion
        https://scikit-learn.org/stable/auto_examples/mixture/plot_gmm_selection.html
        https://stats.stackexchange.com/questions/384556/how-to-infer-the-number-of-states-in-a-hidden-markov-model-with-gaussian-mixture

    """
    bic = np.log(len(X)) * k - 2 * likelihood_fn(X)
    return bic


def calculate_bic(model, n_components, X):

    n_features = model.n_features
    # Calculate number of free parameters
    # free_parameters = for_means + for_covars + for_transmat + for_startprob
    # for_means & for_covars = n_features*n_components
    # more on this: https://github.com/hmmlearn/hmmlearn/blob/38b3cece4a6297e978a204099ae6a0a99555ec01/lib/hmmlearn/hmm.py#L186
    # after rewriting transmat, free params is just 1?
    free_parameters_old = 2 * (n_components * n_features) + n_components * (n_components - 1) + (n_components - 1)
    free_parameters = model._get_n_fit_scalars_per_param()

    # logging.info(f'BIC DoF --- 2*(n_components*n_features) + n_components*(n_components-1) + (n_components-1): {free_parameters_old}')
    free_parameters["t"] = 1
    # logging.info(f'BIC DoF --- model._get_n_fit_scalars_per_param(): {free_parameters}')
    free_parameters = sum(free_parameters.values())
    # logging.info(f'BIC DoF --- sum(model._get_n_fit_scalars_per_param()): {free_parameters}')

    bic_score = bic_general(model.score, free_parameters, X)

    return bic_score


def hmm_based_andon_tag(df, feature_name, n_hidden_states=2):
    obs_seq = np.array(df[[feature_name]])

    ghmm = GaussianHMM(
        n_components=n_hidden_states,
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
    if 2 == n_hidden_states:
        ghmm.transmat_ = np.array([[1 - trans, trans], [trans, 1 - trans]])
        logprob, state_seq = ghmm.decode(obs_seq)

        score = ghmm.score(obs_seq)
        bic_score = calculate_bic(ghmm, n_hidden_states, obs_seq)
    elif 3 == n_hidden_states:
        ghmm.transmat_ = np.array([[1 - trans, trans / 2, trans / 2], [trans / 2, 1 - trans, trans / 2], [trans / 2, trans / 2, 1 - trans]])
        logprob, state_seq = ghmm.decode(obs_seq)

        score = ghmm.score(obs_seq)
        bic_score = calculate_bic(ghmm, n_hidden_states, obs_seq)
    else:
        logprob, state_seq = 0, np.ones(obs_seq.shape[0])
        score = 0
        bic_score = 0

    return logprob, score, bic_score, state_seq


def bic_based_hmm_cross_validation(df, feature_name="mhp", n_hidden_states: List[int] = [2, 3]):

    """source: https://scikit-learn.org/stable/auto_examples/mixture/plot_gmm_selection.html"""

    logging.info(f"Starting BIC based cross validation for hidden states")

    lowest_bic = np.inf
    bic = []
    likeliest_result = None
    for state in n_hidden_states:
        logprob, score, bic_score, state_seq = hmm_based_andon_tag(df, feature_name="mhp", n_hidden_states=state)
        logging.info(f"hidden states with n_comps: {state}  -  bic_score: {bic_score}, logprob: {logprob}, hmm.score(): {score}")

        if bic_score < lowest_bic:
            likeliest_result = {"n_states": state, "bic_score": bic_score, "state_seq": state_seq}
            lowest_bic = bic_score

    logging.info(f'lowest_bic score: {likeliest_result["bic_score"]} for n_hidden_states {likeliest_result["n_states"]}')

    return likeliest_result["state_seq"]


def relabel_active_states(tagged_states):

    """
    relabel states so that only "active" states, ie one with the highest mean gets labeled as 1
    and everything else is considered to be 0 or in down/idle state.
    """

    active_state = tagged_states.max()
    tagged_states.loc[:] = np.where(tagged_states == active_state, 1, 0)
    return tagged_states


def generate_tagged_data(df):
    # logprob, state_seq = hmm_based_andon_tag(df, feature_name='mhp')
    # logprob,score,bic_score, state_seq = hmm_based_andon_tag(df, feature_name='mhp')
    state_seq = bic_based_hmm_cross_validation(df, feature_name="mhp", n_hidden_states=[2, 3])
    tagged_states = pd.Series(state_seq, index=df.index)
    tagged_states = utils.mean_based_state_ranking(df.mhp, tagged_states)
    tagged_states = relabel_active_states(tagged_states)

    return tagged_states
