#!/usr/bin/env sh
# Start Speaches with a persistent Docker volume for local models.
docker run --rm --name mavis-speaches -p 8000:8000 -v mavis-speaches-cache:/home/ubuntu/.cache/huggingface ghcr.io/speaches-ai/speaches:latest-cpu
