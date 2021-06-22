# accelerometer-calibration-dashboard
   Plotly dash based dashboard for calibrating a simple machine up time detecting algorithm. 
The code used for calibrating the algorithm is called from Azure Functions running locally in a docker container.
The clustering of the calibration period is performed by a Hidden Markov model.

## Setup:
 - Using compose file:
   - docker-compose up -d
 - Once running the dashboard can be reached on localhost in the browser:
   - http://localhost:8050/
 
## Tutorial:
