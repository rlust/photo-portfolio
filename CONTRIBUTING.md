# Contributing to Photo Portfolio

Thank you for your interest in contributing to the Photo Portfolio project! We appreciate your time and effort in helping us improve this project.

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report any unacceptable behavior to the project maintainers.

## How Can I Contribute?

### Reporting Bugs

Bugs are tracked as [GitHub issues](https://github.com/yourusername/photo-portfolio/issues). Before creating a new issue:

1. **Check if the issue has already been reported** - Search through the existing issues to see if someone else has reported the same issue.
2. **Provide detailed information** - Include a clear title and description, steps to reproduce the issue, expected vs. actual behavior, and any relevant screenshots or error messages.
3. **Include version information** - Specify the version of the application, operating system, and any other relevant software.

### Suggesting Enhancements

We welcome suggestions for new features and improvements. When suggesting an enhancement:

1. **Check if the enhancement has already been suggested** - Search through the existing issues to see if someone else has made a similar suggestion.
2. **Provide a clear and detailed description** - Explain the problem you're trying to solve and why this enhancement would be valuable.
3. **Include examples** - If possible, provide examples of how the enhancement would work.

### Pull Requests

We welcome pull requests that address bugs or add new features. Here's how to submit a pull request:

1. **Fork the repository** - Create a fork of the repository to your GitHub account.
2. **Create a branch** - Create a feature branch for your changes.
   ```
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** - Implement your changes following the project's coding standards.
4. **Write tests** - Ensure that your changes are covered by tests.
5. **Run tests** - Make sure all tests pass before submitting your pull request.
   ```
   make test
   ```
6. **Commit your changes** - Write clear, concise commit messages.
   ```
   git commit -m "Add your commit message here"
   ```
7. **Push to the branch** - Push your changes to your fork.
   ```
   git push origin feature/your-feature-name
   ```
8. **Submit a pull request** - Open a pull request against the `main` branch of the original repository.

## Development Setup

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- Docker and Docker Compose (for local development)
- Google Cloud SDK (for deployment)

### Getting Started

1. **Fork and clone the repository**
   ```
   git clone https://github.com/yourusername/photo-portfolio.git
   cd photo-portfolio/backend
   ```

2. **Set up the development environment**
   ```
   # Install dependencies
   poetry install --with dev
   
   # Activate the virtual environment
   poetry shell
   ```

3. **Set up environment variables**
   Copy the example environment file and update it with your configuration:
   ```
   cp .env.example .env
   ```

4. **Run the application locally**
   ```
   make run
   ```

5. **Run tests**
   ```
   make test
   ```

## Coding Standards

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code.
- Use type hints for all function signatures.
- Write docstrings for all public functions and classes following the Google style guide.
- Keep functions small and focused on a single responsibility.
- Write tests for all new functionality.

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages. This helps with generating changelogs and versioning.

Example commit messages:

```
feat: add user authentication
fix: resolve image upload issue
docs: update API documentation
chore: update dependencies
```

## License

By contributing to this project, you agree that your contributions will be licensed under the project's [LICENSE](LICENSE) file.
