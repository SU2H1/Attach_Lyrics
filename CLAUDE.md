# Claude Code Instructions

## Git Operations

When committing changes:
1. Stage all changes
2. Create descriptive commit messages
3. Push to the main branch

### Commands to run:
```bash
git add .
git commit -m "feat: Add lyrics scraper with Puppeteer and GUI"
git push origin main
```

## Testing Commands

### Install dependencies:
```bash
npm install
pip install -r requirements.txt
```

### Run the application:
```bash
python gui_app.py
```

### Run tests (if available):
```bash
python -m pytest tests/
```

## Code Style

- Follow PEP 8 for Python code
- Use descriptive variable names
- Add type hints where appropriate
- Keep functions focused and single-purpose