# CLAUDE.md — Wilson Virtual Assistant

## Project Overview

Wilson is a virtual assistant project. The repository is in its early stages of development.

- **Repository**: Wilson (Wilson-Virtual-Assistant)
- **Default branch**: `master`

## Repository Structure

```
Wilson/
├── CLAUDE.md          # This file — guidance for AI assistants
└── README.md          # Project README
```

As the project grows, update this section to reflect new directories and modules.

## Development Workflow

### Git Conventions

- **Default branch**: `master`
- **Feature branches**: Use descriptive branch names prefixed with your context (e.g., `claude/feature-name-sessionId`)
- **Commit messages**: Write clear, concise commit messages that describe *why* the change was made, not just what changed
- **Push**: Always use `git push -u origin <branch-name>`

### Code Style

No language or framework has been chosen yet. When code is added, update this section with:
- Language and runtime versions
- Linting and formatting tools (e.g., ESLint, Prettier, Black, Ruff)
- Naming conventions (files, variables, functions, classes)

### Testing

No test framework has been configured yet. When tests are added, document:
- How to run tests (e.g., `npm test`, `pytest`)
- Test file naming conventions
- Coverage requirements

### Building and Running

No build system has been configured yet. When one is added, document:
- How to install dependencies
- How to build the project
- How to run the application locally

## Guidelines for AI Assistants

1. **Read before editing** — Always read a file before modifying it. Understand existing code and conventions before making changes.
2. **Minimal changes** — Only make changes that are directly requested or clearly necessary. Avoid over-engineering.
3. **No guessing** — If requirements are unclear, ask for clarification rather than making assumptions.
4. **Security first** — Never introduce vulnerabilities (injection, XSS, etc.). Never commit secrets or credentials.
5. **Keep this file updated** — When you add significant structure (new directories, frameworks, build tools, test setups), update the relevant sections of this file so future sessions have accurate context.
