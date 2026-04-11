# Contributing to Cognition Env

Thank you for your interest in contributing to Cognition Env! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Focus on the code, not the person
- Help others learn and grow

## How to Contribute

### 1. Reporting Issues

Issues should be reported on GitHub with:
- Clear title describing the problem
- Steps to reproduce
- Expected vs. actual behavior
- Environment (OS, Python version, etc.)
- Relevant logs or screenshots

### 2. Proposing Enhancements

For new features:
- Discuss major changes in an issue first
- Explain the use case and benefits
- Provide sketches or examples if helpful

### 3. Submitting Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make focused changes
4. Add/update tests (if applicable)
5. Ensure code quality:
   ```bash
   # Run any linters/formatters if present
   python -m pytest  # if tests exist
   ```
6. Commit with clear messages: `git commit -m "Add feature X"`
7. Push and create a pull request

### Code Style

- Follow PEP 8 conventions
- Use type hints for new functions
- Add docstrings to public functions
- Keep lines under 100 characters (where practical)

## Development Setup

```bash
# Clone and install in development mode
git clone https://github.com/PSG72-cmd/Cognition-Env.git
cd Cognition-Env
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Testing

Run the environment locally:

```bash
# Terminal 1: Start server
python -m uvicorn ticket_triage_env.server.app:app --port 8000

# Terminal 2: Test with examples
python examples.py
```

## Documentation

- Update [README.md](README.md) for user-facing changes
- Update [ARCHITECTURE.md](ARCHITECTURE.md) for system design changes
- Update [GETTING_STARTED.md](GETTING_STARTED.md) for setup/usage changes
- Add docstrings to all new functions/classes

## Areas for Contribution

- **New task difficulties** — Add grader_advanced.py and corresponding task
- **Alternative baselines** — Implement different agent strategies
- **Performance optimizations** — Speed up grading or server
- **Documentation** — Improve clarity, add examples, translations
- **Testing** — Add test coverage for core functionality
- **UI/Frontend** — Build a dashboard for monitoring training

## Questions?

- Check documentation: [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md)
- Open a GitHub Discussion
- Email the maintainers

Thank you for contributing! 🙏
