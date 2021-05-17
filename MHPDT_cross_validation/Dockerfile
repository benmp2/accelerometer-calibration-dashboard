FROM mcr.microsoft.com/azure-functions/python:3.0-python3.7

ENV AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Add files from this repo to the root site folder.
COPY . /home/site/wwwroot

# Install requirements
RUN cd /home/site/wwwroot && pip install -r azure_py_requirements.txt