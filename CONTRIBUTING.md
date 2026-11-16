# Contributing to Universal Media Converter

Thank you for helping improve Universal Media Converter (UMC).
UMC aims to make media conversion simple, reliable and safe for everyone,
so contributions should favour simplicity, honest quality reporting and
cross-platform behaviour (Windows, macOS and Linux).

## Licensing

UMC is released under the [MIT License](LICENSE). By submitting a contribution,
you agree that it is licensed under the same terms.

## Development setup

1. Install Python 3.10+ and FFmpeg (see the [README](README.md#install)).
2. Fork the repository and clone your fork.
3. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   ```powershell
   .venv\Scripts\Activate.ps1          # Windows PowerShell
   ```

   ```bash
   source .venv/bin/activate           # macOS / Linux
   ```

4. Install UMC in editable mode with the development tools:

   ```bash
   pip install -e ".[dev]"
   ```

## Before submitting changes

```bash
python -m ruff format src tests
python -m ruff check src tests
python -m pytest -q
```

`tests/test_integration.py` runs real FFmpeg conversions on tiny generated
files. These tests are skipped when FFmpeg is not installed; GitHub Actions runs
them on Windows, macOS and Linux for every pull request.

## Pull requests

- Keep changes focused and easy to review.
- Add tests for new behaviour, including a real conversion where it matters.
- Never weaken the safety rules: no overwriting without `--overwrite`, no partial
  files left behind, and the `Quality:` line must stay truthful.
- Update the README and CHANGELOG when user-facing behaviour changes.
- Do not commit media files; generate test media with FFmpeg instead.

## Project layout

```text
src/umc/cli.py            command-line interface
src/umc/core/converter.py runs FFmpeg safely, with fallbacks and progress
src/umc/core/original.py  the default "keep original quality" planner
src/umc/core/presets.py   high / balanced / small / copy presets
src/umc/core/tracks.py    keeps every track when saving MKV
src/umc/core/formats.py   supported formats
src/umc/core/batch.py     output naming and folder scanning
src/umc/core/timecode.py  reading times such as 1:30 for --at
src/umc/core/probe.py     media inspection with FFprobe
tests/                    unit tests and real-FFmpeg integration tests
```

## Releasing (maintainers)

1. Update `__version__` in `src/umc/__init__.py` and add the release to `CHANGELOG.md`.
2. Merge to `main` and wait for the tests to pass.
3. On GitHub, create a release with the tag `vX.Y.Z` (matching the version).
4. The **Publish to PyPI** workflow tests, builds and uploads the package automatically.
