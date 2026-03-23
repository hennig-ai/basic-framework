# Contributing to Basic Framework

Thank you for your interest in contributing!

## How to Report Bugs

Please use the [issue tracker](https://github.com/hennig-ai/basic-framework/issues) and select the **Bug Report** template. Include:
- Python version and OS
- Minimal reproducible example
- Expected vs. actual behavior

## How to Request Features

Open an issue using the **Feature Request** template and describe the use case.

## How to Submit a Pull Request

1. Fork the repository and create a branch from `main`
2. Install dev dependencies: `pip install -r requirements-dev.txt`
3. Make your changes, following the existing code style (type hints on all parameters and return values)
4. Run tests: `python -m pytest tests/`
5. Run type checking: `mypy src/basic_framework --ignore-missing-imports`
6. Open a pull request against `main`

## Code Style

- Full type hints on all functions and methods
- Use `log_and_raise()` instead of bare `raise` (see `basic_framework.proc_frame`)
- No graceful degradation / silent fallbacks — fail fast with clear error messages
- No wildcard imports

## Development Setup

```bash
git clone https://github.com/hennig-ai/basic-framework.git
cd basic-framework
pip install -e .
pip install -r requirements-dev.txt
python -m pytest tests/
```
