# Artifactor Tool

This directory contains the Python package for the Artifactor CLI tool.

## Quick Start

See the [main README](../README.md) for installation and usage instructions.

From the repository root:
```bash
make install  # Install package
make test     # Run tests
```

## Package Structure

```
src/artifactor/
├── __init__.py       # Package initialization
├── cli.py            # Typer-based CLI with subcommands
├── models.py         # Article dataclass schema
├── generator.py      # Post generation and rendering logic
└── templates/        # Jinja2 templates for post output
```

## Development Notes

- Uses Typer for CLI with proper subcommand structure
- Jinja2 for templating with deterministic output
- PyYAML for stable YAML front matter generation
- All tests verify byte-for-byte deterministic generation

## Testing Directly

If you need to run tests from this directory:

```bash
python3 -m pytest -v
python3 -m pytest --cov=artifactor --cov-report=term-missing
```
