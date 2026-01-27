# AGENTS.md

Local guidance for coding agents working in this repository.

## Package manager
- Use `uv` for installs and command execution.
- Prefer `uv run ...` for tooling (`pytest`, `black`, `ruff`, `mypy`, `isort`).

## Formatting and linting
- Formatting: `uv run black m3s tests examples`
- Linting: `uv run ruff check m3s tests examples`
- Auto-fix: `uv run ruff check --fix m3s tests examples`

## Tests
- `uv run pytest`
- Use `uv run pytest <path>` for targeted runs.

## Notes
- The main package is `m3s`; `a5-py` is a separate subproject.

## Workflow
- Keep changes focused and avoid unrelated edits.
- Update or add docs when behavior changes.
- Add tests for new features or bug fixes when feasible.

## Tooling preference
- Use `uv` over `pip` for local dev and CI parity.
- If a command needs an env, prefer `uv run`.
