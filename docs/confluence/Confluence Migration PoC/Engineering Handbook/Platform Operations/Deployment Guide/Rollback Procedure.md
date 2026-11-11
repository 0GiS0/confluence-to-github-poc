---
tags:
  - operations
  - deployment
---

[Engineering Handbook](../../README.md) > [Platform Operations](../README.md) > [Deployment Guide](README.md)

# Rollback Procedure

> [!CAUTION]
> Rollback is only safe for backward compatible migrations.

1. Freeze the pipeline.
2. Redeploy the previous image tag.
3. Verify health endpoints.

```bash
kubectl -n payments rollout undo deploy/payments-api
```
