# Contributing to Enterprise AI DMS

Thank you for your interest in contributing to Enterprise AI Document Management System! This document provides guidelines and instructions for contributing.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inclusive environment for all contributors.

### Our Standards
- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites
- Python 3.14+
- Node.js 18+
- Docker & Docker Compose
- Git

### Setup Development Environment

1. **Fork the repository**
   ```bash
   # Fork the repository on GitHub
   git clone https://github.com/your-username/Enterprise-AI-DMS-Blueprint.git
   cd Enterprise-AI-DMS-Blueprint
   ```

2. **Set up remote**
   ```bash
   git remote add upstream https://github.com/original-owner/Enterprise-AI-DMS-Blueprint.git
   ```

3. **Run setup script**
   ```bash
   # Linux/Mac
   ./scripts/setup.sh
   
   # Windows
   scripts\setup.bat
   ```

4. **Start development environment**
   ```bash
   # Quick start
   ./scripts/quick-start.sh
   ```

## Development Workflow

### Branch Strategy
- `main` - Production branch
- `develop` - Development branch
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches
- `hotfix/*` - Hotfix branches

### Creating a Feature Branch

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make your changes
# Commit your changes
git add .
git commit -m "Add your feature"

# Push to your fork
git push origin feature/your-feature-name
```

### Syncing with Upstream

```bash
# Fetch upstream changes
git fetch upstream

# Merge upstream changes
git checkout develop
git merge upstream/develop

# Push to your fork
git push origin develop
```

## Coding Standards

### Python (Backend)
- Follow PEP 8 style guide
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions short and focused
- Use type hints where appropriate

Example:
```python
def process_document(
    document_id: int,
    file_path: str,
    options: Dict[str, Any] = None
) -> Document:
    """
    Process a document with AI-powered analysis.
    
    Args:
        document_id: The ID of the document to process
        file_path: Path to the document file
        options: Optional processing options
        
    Returns:
        Processed document with analysis results
    """
    # Implementation
    pass
```

### JavaScript/TypeScript (Frontend)
- Follow ESLint rules
- Use meaningful variable names
- Add JSDoc comments
- Use modern ES6+ syntax
- Keep components small and focused

Example:
```typescript
/**
 * Document upload component
 * Handles file upload with progress tracking
 */
const DocumentUpload: React.FC = () => {
  // Implementation
};
```

### Git Commit Messages

Follow conventional commits format:
```
type(scope): subject

body

footer
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(auth): add 2FA support

Implement two-factor authentication using TOTP
with backup codes and SMS fallback.

Closes #123
```

```
fix(api): resolve document upload timeout

Increase timeout for large file uploads
and add progress tracking.

Fixes #456
```

## Testing

### Backend Tests
```bash
cd dms
source venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest tests/test_services.py

# Run with coverage
pytest --cov=app --cov-report=html
```

### Frontend Tests
```bash
cd app

# Run tests
npm test

# Run with coverage
npm test -- --coverage
```

### Test Coverage Requirements
- Unit tests: 70%+ coverage
- Integration tests: All API endpoints
- E2E tests: Critical user workflows

## Documentation

### Code Documentation
- Add docstrings to all functions and classes
- Document complex algorithms
- Add inline comments for unclear logic
- Keep documentation up-to-date

### API Documentation
- Update API_DOCUMENTATION.md for new endpoints
- Add examples for new features
- Document breaking changes

### README Updates
- Update README.md for new features
- Add installation instructions for new dependencies
- Update feature list

## Pull Request Process

### Before Submitting PR
1. Ensure your code follows coding standards
2. Run tests and ensure they pass
3. Update documentation
4. Write descriptive commit messages
5. Sync with upstream develop branch

### Creating Pull Request

1. **Update your branch**
   ```bash
   git checkout feature/your-feature
   git pull upstream develop
   ```

2. **Push your changes**
   ```bash
   git push origin feature/your-feature
   ```

3. **Create Pull Request**
   - Go to GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill out PR template

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] All tests passing
```

### Review Process
1. Automated checks (CI/CD)
2. Code review by maintainers
3. Address review comments
4. Approval and merge

## Issues

### Reporting Bugs
Use the issue tracker to report bugs:
- Provide clear description
- Include steps to reproduce
- Add relevant logs/screenshots
- Specify environment details

### Feature Requests
Use the issue tracker for feature requests:
- Describe the feature
- Explain use case
- Provide implementation suggestions

## Development Tools

### Recommended IDEs
- **Backend**: VS Code with Python extension
- **Frontend**: VS Code with ESLint extension
- **Mobile**: VS Code with React Native extension

### Useful Extensions
- Python (Microsoft)
- ESLint (Microsoft)
- Prettier (Prettier)
- GitLens (GitKraken)
- Docker (Microsoft)

## Questions?

For questions about contributing:
- Open an issue on GitHub
- Contact maintainers
- Join our Discord community

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Enterprise AI DMS! 🚀