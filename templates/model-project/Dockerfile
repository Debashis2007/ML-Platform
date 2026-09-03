FROM public.ecr.aws/docker/library/python:3.11-slim
WORKDIR /opt/ml/code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY examples/credit-risk/ .
ENV PYTHONUNBUFFERED=1
