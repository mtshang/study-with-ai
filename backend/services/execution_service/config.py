"""Dedicated runner configuration; never load database or personal model settings."""
import os
from pathlib import Path
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[3]
values=dotenv_values(ROOT/'.env.runner',interpolate=False)
KEY=values.get('RUNNER_SERVICE_KEY','')
IMAGE=values.get('RUNNER_IMAGE','')
DOCKER=values.get('RUNNER_DOCKER') or ('C:/Program Files/Docker/Docker/resources/bin/docker.exe' if os.name=='nt' else '/usr/bin/docker')
LABEL='study-with-ai.python-runner=1'
