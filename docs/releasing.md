# Release Process

This document describes how to build and publish Artifactor to PyPI.

## Prerequisites

- Python 3.10 or higher
- PyPI account with API token configured
- TestPyPI account (optional, for testing releases)

## Pre-release Checklist

1. Ensure all tests pass locally
2. Update version in `tool/src/artifactor/__init__.py`
3. Update CHANGELOG or release notes if applicable
4. Commit version bump: `git commit -am "bump version to X.Y.Z"`
5. Create and push tag: `git tag vX.Y.Z && git push origin vX.Y.Z`

## Building the Distribution

Create a clean virtual environment and install build dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

Run the test suite to ensure everything works:

```bash
pytest -q tool/tests
```

Build source distribution and wheel:

```bash
python -m build
```

This creates two files in `dist/`:
- `artifactor-X.Y.Z.tar.gz` (source distribution)
- `artifactor-X.Y.Z-py3-none-any.whl` (wheel)

Verify package metadata:

```bash
twine check dist/*
```

## Publishing to TestPyPI (Optional)

Test the release process on TestPyPI first:

```bash
twine upload --repository testpypi dist/*
```

Install from TestPyPI to verify:

```bash
pip install --index-url https://test.pypi.org/simple/ --no-deps artifactor
artifactor --help
```

## Publishing to PyPI

Upload to production PyPI:

```bash
twine upload dist/*
```

You will be prompted for your PyPI credentials. Alternatively, configure `~/.pypirc` with API tokens:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-...

[testpypi]
username = __token__
password = pypi-...
```

## Post-release

1. Verify package installation: `pip install artifactor`
2. Test console entry point: `artifactor --help`
3. Announce release (GitHub Releases, social media, etc.)
4. Clean up build artifacts: `rm -rf dist/ build/ *.egg-info`

## Troubleshooting

**Build fails with "No module named X"**: Ensure you installed with `pip install -e ".[dev]"`

**Twine check fails**: Review package metadata in `pyproject.toml`

**Import errors after install**: Check `[tool.setuptools.packages.find]` configuration

**Console script not found**: Verify `[project.scripts]` entry point in `pyproject.toml`
