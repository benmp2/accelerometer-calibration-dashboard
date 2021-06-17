import logging
import azure.functions as func
import json
import os
import sys

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, dir_path)

import numpy as np
import utils
import micro_filter
import hmm_tagging
import mhpdt_cross_validation as mhpdt_cv

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    """
    Performs cross validation for MHPDT.

    Command to use when running locally (first cd into directory containing the .json file):
    on linux:                
        curl --request POST 'http://localhost:7071/api/MHPDT_cross_validation' --header 'Content-Type: application/json' --data @mhpdt_calibration_data.json
    on windows (powershell): 
        curl.exe --request POST 'http://localhost:7071/api/MHPDT_cross_validation' --header 'Content-Type: application/json' --data '@mhpdt_calibration_data.json'
    """
    logging.info("MHPDT cross validation function is processing a request.")

    result = None

    try:
        req_body = req.get_json()
    except ValueError:
        logging.info("unable to load json")
        return func.HttpResponse("Bad input", status_code=400)
    else:
        calibration_data = req_body.get("downTimeCalibrationData")
        if not calibration_data:
            return func.HttpResponse("downTimeCalibrationData missing from JSON body.", status_code=400)
        
        logging.info("downTimeCalibrationData successfully loaded, converting json to dataframe.")

        df = data_preprocessing(calibration_data)
        result = perform_calibration(df) 

    if result:
        body = json.dumps(result)
        return func.HttpResponse(
            body=body,
            mimetype="application/json",
        )
    else:
        return func.HttpResponse("No result from function", status_code=500)


def data_preprocessing(calibration_data):

    df = utils.generate_basic_df(calibration_data)
    df = utils.add_features_to_df(df,mhp_window_size='6s')
    df = utils.drop_transient_mhp_window_sized_data(df,mhp_window_size='6s')

    return df

def perform_calibration(df):
    
    logging.info("Running HMM based data tagging.")
    tagged_states = hmm_tagging.generate_tagged_data(df)
    
    number_of_states = np.unique(tagged_states,return_counts=True)
    logging.info(f'number of states: {number_of_states}')
    if number_of_states[0].size < 2:
        return func.HttpResponse("ERROR: Single state found. Unable to tag downTimeCalibrationData automatically.", status_code=400)

    logging.info("Running optimization MHPDT cross validation.")
    cv_result = mhpdt_cv.run_optimization(df, tagged_states)
    
    # preparing message: converting numpy data types to python datatypes for json 
    result = {
        "model_type": "MHPDT",
        "model_params": {
            "mhp_threshold": float(round(cv_result.x[0], 3)),
            "min_cycle_time": 0,
            "andon_uptime_threshold": 5,
            "up_filter_size": int(cv_result.x[1]),
            "down_filter_size": int(cv_result.x[2]),
            "first_filter": cv_result.x[3]
        },
    }

    logging.info("Calculating calibration accuracy.")
    optimization_status,calibration_score = mhpdt_cv.optimization_score(df, result, tagged_states)
    logging.info(f"Calibration accuracy:{calibration_score}")
    result["calibration_status"] = optimization_status
    result["calibration_score"] = calibration_score

    return result