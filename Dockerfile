# Use python base image
FROM python:3.10-slim-buster

# Update packages, install git, and clean up
RUN apt-get update \
    && apt-get install -y git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

#copy requirements.txt to working directory
COPY requirements.txt .

#update pip & install dependencies
RUN --mount=type=cache,target=/root/.cache/pip pip install --upgrade -r requirements.txt 
