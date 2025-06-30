# Project Agents.md Guide for OpenAI Codex

This Agents.md file provides guidelines for OpenAI Codex and other AI agents contributing to this repository.

## Project Structure for OpenAI Codex Navigation

- `/src`: Python source code
  - `/app`: Flask application entry point and HTTP routes
  - `/data`: Data processing logic and storage helpers
  - `/visualization`: Plotly chart generation utilities
- `/templates`: Jinja2 HTML templates for the web UI
- `/static`: CSS and JavaScript assets used by the frontend
- `/tests`: Pytest unit tests that should be maintained and extended

## Coding Conventions for OpenAI Codex

### General Conventions for Agents.md Implementation

- Use Python 3 style with type hints for all new code
- Follow existing formatting in each file and keep functions small and focused
- Choose meaningful variable and function names
- Add comments explaining complex logic or algorithms

### Flask Application Guidelines for OpenAI Codex

- Route handlers live in `src/app/app.py`
- Keep routes concise and delegate heavy logic to modules under `src/data` or `src/visualization`
- Ensure that uploaded files and reports respect the directories listed in `.gitignore`

### Chart Generation Guidelines for OpenAI Codex

- Plotly is used for all visualization functions
- Return Plotly figures as JSON strings for use in the frontend
- Reuse helpers in `src/visualization/charts.py` when adding new charts

### Testing Standards for OpenAI Codex

- Use `pytest` for all tests
- Place new tests in the `tests/` directory
- Prefer small, focused unit tests that verify individual functions

## Testing Requirements for OpenAI Codex

Before opening a pull request, run:

```bash
# Run all tests
pytest

# Run a specific test file
pytest path/to/test_file.py

# Run tests with coverage report
pytest --cov=src
```

## Pull Request Guidelines for OpenAI Codex

1. Provide a clear description of the changes and reference any relevant issues
2. Ensure all tests pass and include new tests when adding features or fixing bugs
3. Keep pull requests focused on a single topic
4. Include screenshots or GIFs for any frontend/UI changes
5. Do not commit secrets or data files—see `.gitignore` and `.env.example`

## Programmatic Checks for OpenAI Codex

There are currently no dedicated lint or type-check scripts in this repository. Always make sure your code runs and tests pass locally before submitting.
