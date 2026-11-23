"""Deploy the FastAPI backend to a Hugging Face Docker Space.

Usage (from the project root, with HF_TOKEN set to a *write* token):
    .venv/bin/python deploy/deploy_hf.py [space-name]     # default: aqi-forecast-api

A Docker Space needs, at the root of its repo:
  - Dockerfile           -> we upload backend/Dockerfile there
  - README.md            -> with YAML metadata (sdk: docker, app_port: 7860)
plus everything the Dockerfile COPYs: src/, backend/, models/.
Hugging Face then builds the image and runs it.
"""
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent

SPACE_README = """---
title: AQI Forecast API
emoji: 🌫️
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# AQI Forecast API

FastAPI backend serving 7-day AQI forecasts (LightGBM) for 9 Indian cities.
Interactive docs at `/docs`. Source: https://github.com/boyatomic83/ai_quality_ML
"""


def main():
    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("HF_TOKEN is not set")
    name = sys.argv[1] if len(sys.argv) > 1 else "aqi-forecast-api"

    api = HfApi(token=token)
    user = api.whoami()["name"]
    repo_id = f"{user}/{name}"

    api.create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True)

    # Root-level files the Space needs.
    api.upload_file(path_or_fileobj=SPACE_README.encode(), path_in_repo="README.md",
                    repo_id=repo_id, repo_type="space")
    api.upload_file(path_or_fileobj=str(ROOT / "backend" / "Dockerfile"), path_in_repo="Dockerfile",
                    repo_id=repo_id, repo_type="space")
    # Code + model artifacts (skip caches and tests to keep the Space small).
    for folder in ("src", "backend", "models"):
        api.upload_folder(folder_path=str(ROOT / folder), path_in_repo=folder,
                          repo_id=repo_id, repo_type="space",
                          ignore_patterns=["**/__pycache__/**", "*.pyc", "tests/**", "Dockerfile"],
                          commit_message=f"Upload {folder}/")

    subdomain = f"{user}-{name}".lower().replace("_", "-").replace(".", "-")
    print(f"Space:   https://huggingface.co/spaces/{repo_id}")
    print(f"API URL: https://{subdomain}.hf.space")


if __name__ == "__main__":
    main()
