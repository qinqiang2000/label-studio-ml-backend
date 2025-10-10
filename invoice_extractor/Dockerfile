FROM python:3.10-slim
ARG TEST_ENV

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=${PORT:-9090} \
    PIP_CACHE_DIR=/.cache \
    WORKERS=1 \
    THREADS=8 \
    PYTHONPATH=/app

# Update the base OS
RUN --mount=type=cache,target="/var/cache/apt",sharing=locked \
    --mount=type=cache,target="/var/lib/apt/lists",sharing=locked \
    set -eux; \
    apt-get update; \
    apt-get upgrade -y; \
    apt install --no-install-recommends -y  \
        git; \
    apt-get autoremove -y

# install base requirements
COPY invoice_extractor/requirements-base.txt .
RUN --mount=type=cache,target=${PIP_CACHE_DIR},sharing=locked \
    pip install -r requirements-base.txt

# Copy the project root label_studio_ml module (modified version with /analyze endpoint)
# Note: This requires building from project root with: docker build -f invoice_extractor/Dockerfile .
COPY label_studio_ml /tmp/label_studio_ml
COPY setup.py /tmp/setup.py
COPY README.md /tmp/README.md
COPY LICENSE /tmp/LICENSE
COPY requirements.txt /tmp/requirements.txt

# install label-studio-ml from local modified version
RUN --mount=type=cache,target=${PIP_CACHE_DIR},sharing=locked \
    cd /tmp && pip install --no-deps . && rm -rf /tmp/label_studio_ml /tmp/setup.py /tmp/README.md /tmp/LICENSE /tmp/requirements.txt

# install custom requirements
COPY invoice_extractor/requirements.txt .
RUN --mount=type=cache,target=${PIP_CACHE_DIR},sharing=locked \
    pip install -r requirements.txt

# install test requirements if needed
COPY invoice_extractor/requirements-test.txt .
# build only when TEST_ENV="true"
RUN --mount=type=cache,target=${PIP_CACHE_DIR},sharing=locked \
    if [ "$TEST_ENV" = "true" ]; then \
      pip install -r requirements-test.txt; \
    fi

COPY invoice_extractor/ .

EXPOSE 9090

CMD python start_with_custom_endpoints.py --host 0.0.0.0 --port $PORT
