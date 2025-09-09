FROM python:3.11-slim

ARG TORCH_VERSION=2.2.0

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV OMP_NUM_THREADS=4
ENV OPENBLAS_NUM_THREADS=4
ENV MKL_NUM_THREADS=4
ENV NUMEXPR_NUM_THREADS=4

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip setuptools wheel

# Instala torch CPU
RUN pip install --no-cache-dir "torch==${TORCH_VERSION}" --index-url https://download.pytorch.org/whl/cpu

# Instala primeiro os pacotes que quebram dependendo da ordem
RUN pip install --no-cache-dir numpy==1.26.4 scipy==1.11.4

RUN pip install --no-cache-dir -r /app/requirements.txt

RUN mkdir -p /workspaces/iris /app/ml/models /app/ml/data /app/static

RUN git config --global --add safe.directory /workspaces/iris

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
