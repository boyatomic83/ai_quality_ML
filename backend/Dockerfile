# AQI Forecast API - works on Hugging Face Spaces (Docker SDK, port 7860).
# Build from the PROJECT ROOT so src/ and models/ are in the build context:
#   docker build -f backend/Dockerfile -t aqi-api .
#   docker run -p 7860:7860 aqi-api
FROM python:3.13-slim

# LightGBM needs the OpenMP runtime, which the slim image does not include.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs containers as user 1000; create it so file
# permissions match locally and on HF.
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

# Install dependencies first: this layer is cached until requirements change.
COPY --chown=user backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --user -r backend/requirements.txt

# Only what the API needs: shared feature code, the API, and saved artifacts.
COPY --chown=user src/ src/
COPY --chown=user backend/ backend/
COPY --chown=user models/ models/

EXPOSE 7860
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "7860"]
