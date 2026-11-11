---
tags:
  - development
  - python
---

[Engineering Handbook](../../README.md) > [Development Practices](../README.md) > [Coding Standards](README.md)

# Python Style

Use type hints and format with `ruff format`.

```python
def add(a: int, b: int) -> int:
    return a + b
```

> [!IMPORTANT]
> Prefer dataclasses for simple value objects.
