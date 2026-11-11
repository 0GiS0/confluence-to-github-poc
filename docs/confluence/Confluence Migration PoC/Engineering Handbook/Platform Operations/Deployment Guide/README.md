---
tags:
  - operations
  - deployment
---

[Engineering Handbook](../../README.md) > [Platform Operations](../README.md)

# Deployment Guide

- [Prerequisites](#deploymentguide-prerequisites)
- [Deploy](#deploymentguide-deploy)
- [Current status](#deploymentguide-currentstatus)
- [Post-deploy checks](#deploymentguide-post-deploychecks)

## Prerequisites

- [x] Access to the Kubernetes cluster
- [x] Release tag approved
- [ ] Change ticket created

## Deploy

Run the pipeline and follow the steps below. See [rollback procedure](Rollback%20Procedure.md) if the rollout fails.

```bash
kubectl -n payments rollout status deploy/payments-api --timeout=5m
```

## Current status

<mark style="background: #baf3db;">PRODUCTION STABLE</mark> <mark style="background: #f8e6a0;">STAGING DEGRADED</mark> 

## Post-deploy checks

Check the dashboards before closing the change.
