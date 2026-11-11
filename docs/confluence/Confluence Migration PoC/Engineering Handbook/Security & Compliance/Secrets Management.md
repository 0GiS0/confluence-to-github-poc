---
tags:
  - security
---

[Engineering Handbook](../README.md) > [Security & Compliance](README.md)

# Secrets Management

Secrets live in the vault. Never commit them to repositories.

```bash
vault kv get secret/payments/api-key
```

Reference: [Access Control Policy](Access%20Control%20Policy.md)
