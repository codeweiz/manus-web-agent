# Contributing to Manus Web Agent

Thank you for your interest in contributing to Manus Web Agent! This document provides guidelines and instructions for contributing.

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install development dependencies:
   ```bash
   make install-dev
   # Or manually:
   pip install -e ".[dev]"
   pip install -r tests/requirements.txt
   ```
4. Copy `.env.example` to `.env` and configure your environment variables
5. Start the development services:
   ```bash
   make db-start
   ```

## Development Workflow

1. Create a new branch for your feature or bug fix
2. Make your changes
3. Run tests to ensure nothing is broken:
   ```bash
   make test
   ```
4. Run linting and formatting:
   ```bash
   make lint
   make format
   ```
5. Commit your changes with clear, descriptive messages
6. Push to your fork and create a pull request

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write docstrings for public functions and classes
- Keep functions focused and modular

## Testing

- Write tests for new functionality
- Ensure all tests pass before submitting PR
- Use pytest for testing
- Use pytest-asyncio for async tests

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Reference issue numbers when applicable

## Questions?

Feel free to open an issue for questions or discussions.
