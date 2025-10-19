FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# system deps for lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# leverage cache
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# app code (no big data/artifacts baked into image)
COPY . /app

# default interactive shell for ad-hoc runs
CMD ["bash"]
