# Pypi deployment

```
uv version --bump patch
uv sync --extra dev
python -m build .
twine check dist/*
twine upload dist/*
```
