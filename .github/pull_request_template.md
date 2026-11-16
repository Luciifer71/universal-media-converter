## Problem and resulting behavior

Explain the user-visible problem and what changes after this PR.

## Verification

- `python -m ruff check src tests`:
- `python -m pytest -q`:
- Real conversions checked (input → output, OS):
- Remaining limitations:

## Scope

Confirm that original-quality defaults, safe file handling (no overwrites,
no partial files) and honest quality reporting remain intact. State any new
dependencies. Do not attach private media files.
