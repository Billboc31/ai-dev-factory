# Stage 1: Build React dashboard
FROM node:20-slim AS dashboard
WORKDIR /build
COPY apps/dashboard/package*.json ./
RUN npm ci
COPY apps/dashboard/ ./
RUN npm run build

# Stage 2: Runtime base image (daemon + control-api)
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY services/control_api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
COPY . /app/

ENV AI_DEV_FACTORY_RUNTIME_ROOT=/runtime
ENV PYTHONPATH=/app

# Stage 3: Web (nginx + compiled dashboard)
FROM nginx:alpine AS web
COPY --from=dashboard /build/dist /usr/share/nginx/html
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
