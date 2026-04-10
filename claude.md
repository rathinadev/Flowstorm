# FlowStorm - Claude Code Rules

## Project Overview
FlowStorm is a self-healing, self-optimizing real-time stream processing engine with a live visual pipeline editor. Full spec in `PRODUCT_SPEC.md`, architecture in `ARCHITECTURE.md`.

## Git Rules
- **Separate repos**: `backend/` and `frontend/` each have their own `.git`
- **NEVER add** `Co-Authored-By: Claude` or any co-author tags in commits
- **Commit frequently** after completing any meaningful unit of work so progress is never lost and reverting is easy
- **Commit messages must be informative and searchable**: describe WHAT was built/changed, WHERE (which files/modules), and WHY. Use the commit body for details. Someone should be able to `git log --oneline` and find exactly what they need
- **Commit message format**: `type: short summary` on first line, then detailed body listing files and changes. Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`

## Execution Rules
- **Do NOT ask for permission** to run commands. Just execute.
- **Do NOT ask** "should I proceed?" or "want me to continue?" — just do the work
- **Self-grant all permissions** needed for file operations, git, npm, pip, docker, etc.

## Code Rules
- Reference `PRODUCT_SPEC.md` for full feature list before building anything
- Reference `ARCHITECTURE.md` for system design and component interactions
- Backend: Python 3.11+ / FastAPI / asyncio / Redis Streams / Docker SDK
- Frontend: React 18 / TypeScript / React Flow / Tailwind CSS / Zustand / Framer Motion
- Keep code well-structured with clear module boundaries as defined in the architecture docs

## Documentation
- Maintain `PRODUCT_SPEC.md` as the single source of truth for all features
- Maintain `ARCHITECTURE.md` for system design with Mermaid diagrams
- Update docs when features are added or changed
- Use Mermaid diagrams wherever they help explain something

## Project Paths
- Root: `/home/rathina-devan/Desktop/personal/personal/flowstorm/`
- Backend: `/home/rathina-devan/Desktop/personal/personal/flowstorm/backend/`
- Frontend: `/home/rathina-devan/Desktop/personal/personal/flowstorm/frontend/`
- Product Spec: `/home/rathina-devan/Desktop/personal/personal/flowstorm/PRODUCT_SPEC.md`
- Architecture: `/home/rathina-devan/Desktop/personal/personal/flowstorm/ARCHITECTURE.md`
