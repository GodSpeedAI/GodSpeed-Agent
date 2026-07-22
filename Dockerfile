# Godspeed Agent Harness — portable container image.
# Builds the godspeed-nav CLI into a runnable image so the harness can be
# used without a local uv/Python toolchain.
#
# Build:
#   docker build -t godspeed-agent .
# Run (mount your workspace so ledgers land in it):
#   docker run --rm -v "$PWD:/work" -w /work godspeed-agent runtime-snapshot \
#     --workspace-root /work --storage-root .godspeed-harness
#
# RuVector semantic search is an optional sidecar (needs Node.js). It is off
# by default to keep the image small. Enable it with:
#   docker build -t godspeed-agent --build-arg INSTALL_RUVECTOR=1 .
FROM python:3.12-slim

# uv: copy the binary from the official image, no curl/install needed.
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/

WORKDIR /app

# Deps first (cached unless requirements change).
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

# Source.
COPY godspeed_nav/ godspeed_nav/
COPY bin/ bin/
COPY mcp/ mcp/
COPY README.md HARNESS.md LICENSE ./

# Optional RuVector bridge.
ARG INSTALL_RUVECTOR=0
COPY tools/ruvector/package.json tools/ruvector/search_memory.cjs ./tools/ruvector/
RUN if [ "$INSTALL_RUVECTOR" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends nodejs npm \
      && rm -rf /var/lib/apt/lists/* \
      && cd tools/ruvector && npm install --omit=dev; \
    fi

# Install the project so the godspeed-nav entrypoint exists in the venv.
RUN uv sync --no-dev

# Put the venv on PATH so `godspeed-nav` resolves regardless of the caller's
# working directory (the CLI is cwd-agnostic; ledgers go where --storage-root points).
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["godspeed-nav"]
CMD ["--help"]
