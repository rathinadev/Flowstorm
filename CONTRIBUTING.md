# Contributing to FlowStorm

Thank you for your interest in contributing to FlowStorm. This document provides
guidelines and instructions for contributing to the project. FlowStorm is a
self-healing, self-optimizing real-time stream processing engine, and we welcome
contributions of all kinds -- bug fixes, new features, documentation improvements,
and testing enhancements.

Please take a moment to read through this guide before submitting your contribution.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Backend Development Guide](#backend-development-guide)
- [Frontend Development Guide](#frontend-development-guide)
- [Project Structure](#project-structure)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Guidelines](#documentation-guidelines)
- [Issue Reporting and Feature Requests](#issue-reporting-and-feature-requests)

## Code of Conduct

All contributors are expected to uphold a respectful and inclusive environment.
By participating in this project, you agree to:

- Use welcoming and inclusive language.
- Respect differing viewpoints and experiences.
- Accept constructive criticism gracefully.
- Focus on what is best for the project and community.
- Show empathy toward other contributors.

Unacceptable behavior includes harassment, trolling, personal attacks, and any
conduct that would be considered inappropriate in a professional setting.
Violations may result in removal from the project.

## Getting Started

### Prerequisites

Ensure the following are installed on your system:

| Requirement    | Version | Required |
|----------------|---------|----------|
| Python         | 3.11+   | Yes      |
| Node.js        | 18+     | Yes      |
| npm            | 9+      | Yes      |
| Redis          | 7.0+    | No (demo mode works without it) |
| PostgreSQL     | 15+     | No (falls back to in-memory storage) |
| Docker         | 24+     | No (demo mode works without it) |

### Fork and Clone

1. Fork the repository on GitHub.
2. Clone your fork locally:

```bash
git clone https://github.com/<your-username>/flowstorm.git
cd flowstorm
```

3. Add the upstream remote:

```bash
git remote add upstream https://github.com/<org>/flowstorm.git
```

### Initial Setup

The quickest way to get the full development environment running:

```bash
chmod +x start.sh && ./start.sh
```

This script creates a Python virtual environment, installs backend and frontend
dependencies in parallel, and starts both servers.

**Manual setup (backend):**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Manual setup (frontend):**

```bash
cd frontend
npm install
npm run dev
```

The backend runs on `http://localhost:8000` and the frontend on
`http://localhost:3000`. Demo mode is available without Redis, Docker, or
PostgreSQL -- simply open the frontend and click **Start Demo**.

## Development Workflow

### Branching Strategy

We use a trunk-based branching model:

- `main` -- stable, production-ready code. Never commit directly to `main`.
- `feature/<short-description>` -- for new features (e.g., `feature/predictive-scaling-api`).
- `fix/<short-description>` -- for bug fixes (e.g., `fix/websocket-reconnect`).
- `docs/<short-description>` -- for documentation changes.
- `refactor/<short-description>` -- for code refactoring with no behavior changes.

Always branch from the latest `main`:

```bash
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name
```

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>          (optional)

<footer>        (optional)
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

**Scopes:** `engine`, `api`, `health`, `optimizer`, `chaos`, `pipeline-git`,
`dlq`, `ab-testing`, `checkpoint`, `demo`, `models`, `workers`, `frontend`,
`dashboard`, `editor`, `store`, `ci`

**Examples:**

```
feat(optimizer): add window optimization strategy for tumbling windows
fix(health): prevent healing loop when cooldown timer races with heartbeat
docs(api): update WebSocket event reference for chaos events
test(engine): add integration tests for DAG compiler with cyclic detection
```

Keep the subject line under 72 characters. Use the imperative mood ("add" not
"added"). Do not end the subject with a period.

### Pull Request Process

1. Ensure your branch is up to date with `main`:

```bash
git fetch upstream
git rebase upstream/main
```

2. Run all tests before submitting (see [Testing Guidelines](#testing-guidelines)).

3. Open a pull request against `main` with:
   - A clear title following the commit message convention.
   - A description explaining **what** changed and **why**.
   - References to related issues (e.g., `Closes #42`).
   - Screenshots or recordings for UI changes.

4. All pull requests require:
   - Passing CI checks (linting, tests, type checking).
   - At least one approving review.
   - No unresolved review comments.

5. Squash and merge is the preferred merge strategy.

## Backend Development Guide

### Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) with a line length limit of 100 characters.
- Use type hints for all function signatures and return types.
- Use `async`/`await` for all I/O-bound operations.
- Use [Pydantic](https://docs.pydantic.dev/) models for data validation and serialization.
- Prefer composition over inheritance for service classes.

**Naming conventions:**

| Element         | Convention           | Example                     |
|-----------------|---------------------|-----------------------------|
| Modules         | `snake_case`        | `dag_compiler.py`           |
| Classes         | `PascalCase`        | `HealthMonitor`             |
| Functions       | `snake_case`        | `detect_anomalies()`        |
| Constants       | `UPPER_SNAKE_CASE`  | `MAX_HEALING_RETRIES`       |
| Private members | `_leading_underscore`| `_calculate_health_score()` |

**Example function:**

```python
async def detect_anomalies(
    metrics: WorkerMetrics,
    thresholds: AnomalyThresholds,
) -> list[AnomalyEvent]:
    """Analyze worker metrics against configured thresholds.

    Args:
        metrics: Current worker metrics snapshot.
        thresholds: Configured anomaly detection thresholds.

    Returns:
        List of detected anomaly events, empty if none found.
    """
    anomalies: list[AnomalyEvent] = []
    # implementation ...
    return anomalies
```

### API Conventions

- All REST endpoints live under `/api/`.
- Use plural nouns for resource names (`/api/pipelines`, not `/api/pipeline`).
- Return appropriate HTTP status codes: `200` for success, `201` for creation,
  `404` for not found, `422` for validation errors.
- Use Pydantic models for both request and response schemas.
- Document endpoints with FastAPI docstrings (auto-generated OpenAPI).
- WebSocket endpoints follow the pattern `/api/ws/<resource>/<id>`.

### Adding a New Operator

When implementing a new operator type:

1. Define the operator model in `backend/src/models/`.
2. Implement the worker class in `backend/src/workers/`, extending `BaseWorker`.
3. Register it in the DAG compiler at `backend/src/engine/compiler.py`.
4. Add corresponding tests in `backend/tests/`.
5. Update the frontend node palette to include the new operator type.

## Frontend Development Guide

### TypeScript Style

- Enable `strict` mode in TypeScript configuration.
- Prefer `interface` over `type` for object shapes unless union types are needed.
- Use explicit return types for exported functions and components.
- Avoid `any`; use `unknown` when the type is genuinely indeterminate.
- Use absolute imports from `src/` (configured via Vite aliases).

**Naming conventions:**

| Element       | Convention          | Example                  |
|---------------|---------------------|--------------------------|
| Components    | `PascalCase`        | `ChaosPanel.tsx`         |
| Hooks         | `camelCase` (use*)  | `useWebSocket.ts`        |
| Stores        | `camelCase` (Store) | `pipelineStore.ts`       |
| Types         | `PascalCase`        | `PipelineNode`           |
| Utilities     | `camelCase`         | `formatMetrics.ts`       |
| Constants     | `UPPER_SNAKE_CASE`  | `MAX_RETRY_COUNT`        |

### Component Patterns

- Use functional components with hooks exclusively (no class components).
- Colocate component-specific types, styles, and utilities within the component
  directory.
- Extract reusable logic into custom hooks under `src/hooks/`.
- Keep components focused on a single responsibility.

**Example component structure:**

```tsx
import { FC, useCallback } from 'react';
import { usePipelineStore } from '../../store/pipelineStore';

interface ChaosControlProps {
  pipelineId: string;
  isRunning: boolean;
}

export const ChaosControl: FC<ChaosControlProps> = ({ pipelineId, isRunning }) => {
  const { startChaos, stopChaos } = usePipelineStore();

  const handleToggle = useCallback(() => {
    if (isRunning) {
      stopChaos(pipelineId);
    } else {
      startChaos(pipelineId);
    }
  }, [pipelineId, isRunning, startChaos, stopChaos]);

  return (
    <button
      onClick={handleToggle}
      className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700"
    >
      {isRunning ? 'Stop Chaos' : 'Start Chaos'}
    </button>
  );
};
```

### State Management Conventions

FlowStorm uses [Zustand](https://github.com/pmndrs/zustand) for state management
with three dedicated stores:

| Store             | Responsibility                                 |
|-------------------|-------------------------------------------------|
| `pipelineStore`   | Pipeline topology, nodes, edges, deployment state |
| `metricsStore`    | Real-time metrics, health scores, throughput    |
| `chaosStore`      | Chaos engineering state, scenarios, results     |

Guidelines for working with stores:

- Keep store slices small and focused.
- Derive computed values with selectors, not by storing redundant state.
- Use the `subscribeWithSelector` middleware for performance-sensitive subscriptions.
- Never mutate state directly; always use the store's setter functions.

### Styling

- Use [Tailwind CSS](https://tailwindcss.com/) utility classes for all styling.
- Follow the existing color palette and spacing conventions defined in
  `tailwind.config.js`.
- Avoid inline styles except for dynamic values (e.g., calculated positions in
  React Flow).
- Use Framer Motion for animations; keep them subtle and purposeful.

## Project Structure

```
flowstorm/
├── backend/
│   ├── src/
│   │   ├── main.py               # FastAPI application entry point
│   │   ├── api/                   # REST endpoints + WebSocket handlers
│   │   ├── engine/                # DAG compiler, scheduler, runtime
│   │   ├── workers/               # Operator implementations (14 types)
│   │   ├── health/                # MAPE-K self-healing system
│   │   ├── optimizer/             # Pattern analyzer + DAG rewriter
│   │   ├── chaos/                 # Chaos engineering scenarios + engine
│   │   ├── pipeline_git/          # Version control, diff, store
│   │   ├── dlq/                   # Dead letter queue diagnostics
│   │   ├── ab_testing/            # A/B test manager
│   │   ├── checkpoint/            # State checkpoint management
│   │   ├── demo/                  # Demo simulator
│   │   └── models/                # Pydantic data models
│   ├── config/                    # Application settings
│   ├── tests/                     # pytest test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx               # Application entry point
│   │   ├── components/            # React components (19 total)
│   │   │   ├── pipeline/          # Visual DAG editor (React Flow)
│   │   │   ├── dashboard/         # Real-time monitoring (Recharts)
│   │   │   ├── chaos/             # Chaos engineering controls
│   │   │   ├── dlq/               # DLQ diagnostics browser
│   │   │   ├── git/               # Version history + visual diff
│   │   │   ├── lineage/           # Data lineage tracer
│   │   │   ├── ab/                # A/B test comparator
│   │   │   └── common/            # Shared components (Header, Sidebar)
│   │   ├── store/                 # Zustand stores (3 stores)
│   │   ├── hooks/                 # Custom hooks (WebSocket, etc.)
│   │   ├── services/              # API client layer (30+ methods)
│   │   └── types/                 # TypeScript type definitions
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── package.json
├── docs/
│   ├── ARCHITECTURE.md            # System architecture + diagrams
│   ├── API_REFERENCE.md           # Full API documentation
│   └── MODULES.md                 # Module deep-dive
├── start.sh                       # One-command startup script
├── LICENSE                        # MIT License
└── README.md
```

## Testing Guidelines

### Backend Testing

We use [pytest](https://docs.pytest.org/) with `pytest-asyncio` for async test
support. All tests reside in `backend/tests/`.

**Running tests:**

```bash
cd backend
source .venv/bin/activate
pytest                        # run all tests
pytest tests/test_engine.py   # run a specific module
pytest -v                     # verbose output
pytest -x                     # stop on first failure
pytest --cov=src              # with coverage report
```

**Test file naming:** `test_<module>.py` (e.g., `test_compiler.py`,
`test_health_monitor.py`).

**Writing tests:**

- Test both success and error paths.
- Use fixtures for reusable test data and mock services.
- Mock external dependencies (Redis, Docker, PostgreSQL) in unit tests.
- Use `pytest.mark.asyncio` for async test functions.
- Aim for meaningful coverage, not just high percentages.

**Example test:**

```python
import pytest
from src.engine.compiler import DAGCompiler
from src.models.pipeline import PipelineDefinition

@pytest.fixture
def sample_pipeline() -> PipelineDefinition:
    return PipelineDefinition(
        name="test-pipeline",
        nodes=[...],
        edges=[...],
    )

@pytest.mark.asyncio
async def test_compiler_detects_cyclic_graph(sample_pipeline):
    compiler = DAGCompiler()
    sample_pipeline.edges.append(cyclic_edge)

    with pytest.raises(ValueError, match="Cyclic dependency detected"):
        await compiler.compile(sample_pipeline)
```

### Frontend Testing

**Running tests:**

```bash
cd frontend
npm run lint                  # ESLint checks
npx tsc --noEmit              # TypeScript type checking
```

**Guidelines:**

- Validate TypeScript types with strict mode enabled.
- Test component rendering and user interactions.
- Test Zustand store logic independently from components.
- Mock API calls and WebSocket connections in tests.

### General Testing Principles

- Write tests alongside your code, not as an afterthought.
- Every bug fix should include a regression test.
- Keep tests independent -- no test should depend on the execution order of
  another.
- Use descriptive test names that explain the expected behavior.

## Documentation Guidelines

- Update documentation when your changes affect public APIs, configuration, or
  user-facing behavior.
- Use clear, concise language. Write for an audience that may not be familiar
  with the codebase.
- API documentation is auto-generated from FastAPI docstrings and Pydantic
  models -- keep them accurate.
- For architectural changes, update `docs/ARCHITECTURE.md`.
- For API changes, update `docs/API_REFERENCE.md`.
- For module-level changes, update `docs/MODULES.md`.
- Use fenced code blocks with language identifiers for all code examples.
- Prefer concrete examples over abstract descriptions.

## Issue Reporting and Feature Requests

### Reporting Bugs

Before opening a new issue, search existing issues to avoid duplicates. When
filing a bug report, include:

1. **Summary:** A clear, concise description of the bug.
2. **Steps to reproduce:** Numbered steps to reproduce the behavior.
3. **Expected behavior:** What you expected to happen.
4. **Actual behavior:** What actually happened.
5. **Environment:** OS, Python version, Node.js version, browser, and relevant
   service versions (Redis, PostgreSQL, Docker).
6. **Logs/Screenshots:** Relevant error messages, console output, or screenshots.
7. **Pipeline configuration:** If the bug relates to pipeline execution, include
   the pipeline JSON definition (sanitize any sensitive data).

### Requesting Features

Feature requests are welcome. When submitting one, include:

1. **Problem statement:** Describe the problem or limitation you are experiencing.
2. **Proposed solution:** Describe your suggested approach.
3. **Alternatives considered:** Note any alternative approaches you evaluated.
4. **Use case:** Explain how this feature would be used in practice.

### Issue Labels

| Label           | Description                                    |
|-----------------|------------------------------------------------|
| `bug`           | Something is not working as expected           |
| `feature`       | New feature request                            |
| `enhancement`   | Improvement to existing functionality          |
| `documentation` | Documentation updates needed                   |
| `good first issue` | Suitable for new contributors              |
| `help wanted`   | Extra attention or expertise needed            |

---

Thank you for contributing to FlowStorm. Your efforts help make real-time stream
processing more resilient, efficient, and accessible.
