ARG BASE=pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime
FROM ${BASE} AS builder

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

ARG FILE=docker/pt2.7-cu128.txt

COPY ${FILE} ./requirements.in

RUN python - <<'PY'
from pathlib import Path

skip = {
    "torch",
    "torchvision",
    "torchaudio",
    "--index-url https://pypi.org/simple",
    "--extra-index-url https://download.pytorch.org/whl/cu118",
    "--extra-index-url https://download.pytorch.org/whl/cu128",
}
lines = Path("requirements.in").read_text().splitlines()
filtered = [line for line in lines if line.strip() not in skip]
Path("requirements.docker.txt").write_text("\n".join(filtered) + "\n")
PY

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-venv \
    build-essential \
    gcc \
    g++ \
    && python -m venv --system-site-packages "$VIRTUAL_ENV" \
    && "$VIRTUAL_ENV/bin/pip" wheel --wheel-dir /wheels -r requirements.docker.txt \
    && rm -rf /var/lib/apt/lists/*

FROM ${BASE}

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

COPY --from=builder /app/requirements.docker.txt ./requirements.docker.txt
COPY --from=builder /opt/venv /opt/venv

RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels,ro \
    "$VIRTUAL_ENV/bin/pip" install --no-compile --no-index --find-links=/wheels -r requirements.docker.txt \
    && rm -rf /root/.cache /tmp/*

CMD ["/bin/bash"]
