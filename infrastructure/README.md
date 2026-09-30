# Infrastructure

This directory contains deferred or deployment-oriented infrastructure that is not required for the Personal Local Edition.

- `docker/` — Dockerfiles and Compose definitions.
- `monitoring/` — Prometheus/Grafana configuration.
- `nginx/` — reverse-proxy configuration.
- `railway/` — legacy Railway deployment artifacts.
- `env/` — deployment environment templates.

Do not enable these components as part of the Personal Local startup path unless the corresponding deployment is intentionally being worked on.
