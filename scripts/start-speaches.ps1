# Start Speaches CPU container with persistent model cache (Docker Desktop must be running).
docker run --rm --name mavis-speaches -p 8000:8000 -v mavis-speaches-cache:/home/ubuntu/.cache/huggingface ghcr.io/speaches-ai/speaches:latest-cpu

