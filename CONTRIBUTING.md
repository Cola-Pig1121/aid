# Contributing Guide

<!-- AUTO-GENERATED from pyproject.toml and source code -->
<!-- Do not edit manually -->

## Development Setup

### Prerequisites

- Python 3.12+
- uv (package manager)

### Installation

```bash
# Clone the repository
cd aid

# Create virtual environment
uv venv

# Activate virtual environment
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Unix/macOS

# Install dependencies
uv sync

# Install dev dependencies
uv sync --group dev
```

## Available Commands

| Command | Description |
|---------|-------------|
| `uv run python -m src.main` | Start the application |
| `uv run pytest` | Run test suite |
| `uv run ruff check src/` | Run linter |
| `uv run ruff check src/ --fix` | Auto-fix linting issues |
| `uv run vulture src/` | Detect dead code |
| `uv run python -m src.main --port 8080` | Run on specific port |
| `uv run python -m src.main --host 127.0.0.1` | Run on localhost only |
| `uv run python -m src.main --debug` | Enable debug mode |

## Project Structure

```text
src/
├── agent/          # ReAct agent implementation
│   ├── base.py     # Base agent class
│   └── react_agent.py  # Medical analysis agent
├── llm/            # LLM client
│   └── client.py   # ModelScope/OpenRouter client
├── tool/           # Agent tools
│   ├── datetime_tool.py
│   ├── location_tool.py
│   ├── memory_tool.py
│   ├── report_parser.py
│   └── search_tool.py
├── ui/             # User interfaces
│   ├── gradio_app.py
│   └── streamlit_app.py
└── main.py         # Entry point
```

## Code Style

This project uses:

- **ruff** for linting and formatting
- **mypy** for type checking

Run before committing:

```bash
uv run ruff check src/ --fix
uv run ruff format src/
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing
```

## Adding New Tools

Tools are implemented by extending `BaseTool` from `langchain_core`:

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    query: str = Field(description="Input description")

class MyTool(BaseTool):
    name: str = "my_tool"
    description: str = "Tool description"
    args_schema: type[BaseModel] = MyToolInput

    def _run(self, query: str) -> str:
        # Implementation
        return result

    async def _arun(self, query: str) -> str:
        return self._run(query)
```

## API Providers

The system supports multiple LLM providers:

1. **ModelScope** (recommended) - Chinese-optimized models
2. **OpenRouter** - Access to various models

Provider is auto-detected based on available API keys.

<!-- END AUTO-GENERATED -->
