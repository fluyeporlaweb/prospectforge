## Summary

What does this pull request change, and why?

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Tests
- [ ] Refactor or chore

## Testing

List the commands you ran and their results:

```bash
ruff check .
mypy src
pytest -m "not apify" -q
```

If you ran the live smoke test, confirm it was capped and that no secrets or personal data were printed:

```bash
APIFY_TOKEN=... pytest -m apify -q
```

## Checklist

- [ ] The change preserves the no-send guarantee.
- [ ] `--dry-run` still makes no Apify or LLM network calls.
- [ ] No tokens, `.env` files, caches, build output, or real lead data are included.
- [ ] Tests cover the new behavior or the bug fix.
- [ ] Documentation is updated when user-facing behavior changes.
- [ ] Commits use conventional commit messages.
