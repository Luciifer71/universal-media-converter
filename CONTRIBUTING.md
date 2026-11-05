# Contributing to Universal Media Converter

Thank you for your interest in contributing to Universal Media Converter (UMC)!

## Getting Started

1. Fork the repository.
2. Clone your fork.
3. Create and activate a Python virtual environment.
4. Install the development dependencies:

   ```bash
   pip install -e ".[dev]"
   ```

## Before Submitting Changes

Run the following checks:

```bash
python -m ruff format src tests
python -m ruff check src tests
python -m pytest -q
```

Make sure all checks pass before submitting your changes.

## Pull Requests

- Keep changes focused and easy to review.
- Include tests for new functionality.
- Update documentation when necessary.
- Explain what your changes do and why they are useful.

## Project Philosophy

UMC aims to make media conversion simple and accessible to everyone.

Contributions should prioritize simplicity, reliability, usability and cross-platform compatibility.

Thank you for helping improve UMC!
