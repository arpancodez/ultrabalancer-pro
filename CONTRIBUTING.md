# Contributing to UltraBalancer Pro

Thank you for your interest in contributing to UltraBalancer Pro! This document provides guidelines for contributing to the project.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Code Standards](#code-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Development Setup](#development-setup)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/ultrabalancer-pro.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Submit a pull request

## Code Standards

### Python Style Guide

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Maximum line length: 100 characters
- Use type hints where applicable
- Write docstrings for all public functions and classes

### Code Organization

```python
# Module docstring
"""Brief description of the module."""

# Imports (stdlib, third-party, local)
import os
import sys

import requests

from ultrabalancer.core import Router

# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Classes and functions
class MyClass:
    """Class docstring.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    """
    
    def __init__(self, param1: str, param2: int):
        self.param1 = param1
        self.param2 = param2
```

### Testing Standards

- Write unit tests for all new functionality
- Maintain minimum 80% code coverage
- Use descriptive test names: `test_<functionality>_<condition>_<expected_result>`
- Mock external dependencies

### Documentation

- Update README.md for new features
- Add docstrings to all public APIs
- Include usage examples for new features
- Update architecture docs when changing core components

## Commit Guidelines

We follow conventional commit format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Commit Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements

### Examples

```bash
feat(router): add weighted round-robin algorithm

Implemented weighted round-robin load balancing algorithm
with configurable weights per backend server.

Closes #123
```

```bash
fix(health-checker): resolve retry backoff calculation

Fixed exponential backoff calculation that was causing
improper retry intervals during health check failures.
```

```bash
docs(readme): update installation instructions

Added detailed steps for pip installation and
configuration examples.
```

## Pull Request Process

### Before Submitting

1. **Run tests**: Ensure all tests pass
   ```bash
   pytest tests/
   ```

2. **Check code style**: Run linters
   ```bash
   flake8 src/
   black --check src/
   mypy src/
   ```

3. **Update documentation**: Add/update relevant docs

4. **Add tests**: Include tests for new functionality

### Submitting a PR

1. Push your branch to your fork
2. Open a pull request against the `main` branch
3. Fill out the PR template completely
4. Link related issues using keywords (Closes #123, Fixes #456)

### PR Title Format

Use the same format as commit messages:
```
feat(scope): description
```

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] No new warnings generated
```

### Review Process

1. At least one maintainer approval required
2. All CI checks must pass
3. Address reviewer feedback
4. Squash commits if requested
5. Maintainer will merge when approved

## Development Setup

### Prerequisites

- Python 3.9+
- pip or poetry
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/arpancodez/ultrabalancer-pro.git
cd ultrabalancer-pro

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install in development mode
pip install -e .
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_router.py

# Run with verbose output
pytest -v
```

### Code Quality Checks

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Project Structure

```
ultrabalancer-pro/
├── src/
│   ├── core/           # Core routing logic
│   ├── health/         # Health checking
│   ├── metrics/        # Metrics collection
│   └── plugins/        # Plugin system
├── tests/              # Test files
├── docs/               # Documentation
├── examples/           # Usage examples
└── config/             # Configuration files
```

## Need Help?

- Check existing issues and discussions
- Open a new issue for bugs or feature requests
- Join our community discussions
- Read the documentation in `/docs`

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

Thank you for contributing to UltraBalancer Pro! 🚀
