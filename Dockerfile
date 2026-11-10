FROM python:3.12-slim

WORKDIR /app

# Copy metadata and source code
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install package
RUN pip install --no-cache-dir .

# Start the MCP server over stdio
ENTRYPOINT ["cortex-mcp", "serve-stdio"]
