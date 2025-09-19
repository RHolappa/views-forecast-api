# Contributing to VIEWS Forecast API

Thank you for your interest in contributing to the VIEWS Forecast API! This project is open for educational purposes and welcomes contributions from everyone.

## How to Contribute

### Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/rholappa/views-forecast-api.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Commit your changes: `git commit -m "Add your descriptive commit message"`
6. Push to your fork: `git push origin feature/your-feature-name`
7. Open a Pull Request

### Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and configure your environment variables

4. Run tests:
   ```bash
   pytest
   ```

### Contribution Guidelines

#### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions small and focused

#### Testing
- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for good test coverage

#### Documentation
- Update README.md if you change functionality
- Document new features and API endpoints
- Add inline comments for complex logic

### Types of Contributions

We welcome:
- Bug fixes
- New features
- Documentation improvements
- Performance optimizations
- Test coverage improvements
- Educational examples and tutorials

### Pull Request Process

1. Ensure your code follows the project's coding standards
2. Update documentation as needed
3. Add tests for new functionality
4. Ensure all tests pass
5. Update CHANGELOG.md with your changes
6. Request review from maintainers

### Reporting Issues

- Use GitHub Issues to report bugs
- Include detailed reproduction steps
- Provide environment information
- Attach relevant logs or screenshots

### Educational Contributions

As this is an educational project, we especially welcome:
- Tutorial contributions
- Example use cases
- Learning resources
- Documentation for beginners

## Code of Conduct

Please note that this project has a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to abide by its terms.

## Questions?

Feel free to open an issue for any questions about contributing!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.