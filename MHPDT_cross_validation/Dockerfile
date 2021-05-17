FROM mcr.microsoft.com/azure-functions/python:3.0-python3.7

ENV AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Add files from this repo to the root site folder.
WORKDIR /home/site/wwwroot
COPY . .

# Install requirements
RUN pip install -r ./MHPDT_cross_validation/azure_py_requirements.txt

EXPOSE 80