# Production Deployment Guide

This document captures concrete steps, manifests and runbook items to deploy and operate Ticolops in production.

## Overview

Artifacts added in this repository:

- `infra/k8s/deployment.yaml` — Kubernetes Deployment, Service and HPA example
- `infra/k8s/ingress.yaml` — Ingress example (nginx) with TLS via cert-manager
- `.github/workflows/ci-cd.yml` — GitHub Actions pipeline to build, push, and deploy
- `backend/app/core/security.py` — FastAPI middleware adding security headers and a simple in-process rate limiter

## Recommended production architecture

- Managed PostgreSQL (RDS / Cloud SQL) with Multi-AZ and automated backups
- Managed Redis (ElastiCache / Cloud Memorystore) for session/cache and pub/sub
- Kubernetes cluster (EKS/GKE/AKS) or managed App Platform
- CDN + object storage for frontend assets (S3 + CloudFront or equivalent)
- Ingress with TLS termination (cert-manager with Let's Encrypt or managed certificates)
- Centralized logging (ELK / Cloud Logging) and metrics (Prometheus + Grafana)
- Error tracking (Sentry or equivalent)

## Quick start (example)

1. Prepare secrets: create a `ticolops-secrets` Kubernetes Secret with `database_url` and `redis_url`.

2. Ensure `kubectl` is configured for the target cluster. Apply manifests:

```bash
kubectl apply -f infra/k8s/deployment.yaml
kubectl apply -f infra/k8s/ingress.yaml
```

3. Provide a KUBECONFIG secret to the CI runner (or configure the runner to use a service account).

4. Configure the GitHub Actions secrets used in `.github/workflows/ci-cd.yml` (if using a different registry or deploy mechanism adjust the workflow accordingly).

## Backups and Disaster Recovery

- Enable automated daily backups for the managed DB and keep at least 7 days of retention.
- Periodically test snapshot restores to a staging cluster.
- Backup critical configuration and secrets (store encrypted copies in a secure vault).
- Maintain a runbook `docs/developer/production-deployment.md` with step-by-step restore commands and a designated on-call contact.

## Security and Rate Limiting

- The repository contains an example `SecurityHeadersMiddleware` and `SimpleRateLimitMiddleware` in `backend/app/core/security.py`.
- For production, prefer ingress- or gateway-level rate limiting (NGINX, Cloud Load Balancer, API Gateway) and distribute rate counters in Redis if across multiple pods.

## Monitoring and Alerting

- Configure Prometheus to scrape application metrics and Kubernetes metrics.
- Create Grafana dashboards for latency, error rates, DB connections, CPU/memory.
- Configure Sentry (or similar) for exception tracking with release tagging.

## Next steps / Tailoring

I can adapt the manifests and the CI pipeline for a specific cloud provider (AWS, GCP, Azure) and add Terraform modules, Helm charts, or Helm values for easier deployment. Tell me which provider and registry you prefer and I'll generate the provider-specific artifacts.
