# Container image for the mcp-api-connect MCP server (stdio transport).
#
# Build:  docker build -t mcp-api-connect .
# Run:    docker run --rm -i mcp-api-connect
#
# stdin/stdout carry the MCP protocol (JSON-RPC over stdio); all logs go to
# stderr. Used by Glama and other MCP hosts that launch the server in a
# container and speak to it over stdio.

FROM python:3.12-slim

# Don't buffer stdout/stderr; no .pyc files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install the package with the MCP transport and the SQLite connector store.
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install ".[mcp,storage]"

# Optional persistence for registered connectors: mount a volume at /data and
# run with -e MCP_API_CONNECT_DB_PATH=/data/connectors.db and
# -e MCP_API_CONNECT_ENCRYPTION_KEY=<fernet-key>. Defaults to an in-memory
# store when unset.

# Run as a non-root user.
RUN useradd --create-home --uid 1000 app \
    && mkdir /data && chown app:app /data
USER app

ENTRYPOINT ["mcp-api-connect"]
