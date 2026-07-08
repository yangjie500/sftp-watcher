# Dev/build image.
# Use this for building and optionally for devcontainer/debug.
FROM cgr.dev/chainguard/python:latest-dev AS developer

USER root

RUN apk add --no-cache \
    graphviz \
    git

WORKDIR /app

# Build stage installs the application into a production venv.
FROM developer AS build

WORKDIR /app

# Copy project source into the build stage.
# Make sure .env, .git, .venv, keys, etc. are excluded using .dockerignore.
COPY . /app

ENV UV_PYTHON_DOWNLOADS=never
ENV PATH="/app/.venv/bin:${PATH}"

# Install only production dependencies and install your app non-editably.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --no-dev --python /usr/bin/python3.14

RUN chmod -R a+rX /app/.venv \
    && chmod -R a+rx /app/.venv/bin

# - owner UID 65532 is commonly the nonroot user in minimal container images
# - group 0 supports OpenShift-style arbitrary UID + root-group write access
# - ug+rwX allows both owner and group to write/traverse directories
RUN mkdir -p /data/database /data/watcher_local_directory \
    && chown -R 65532:0 /data \
    && chmod -R ug+rwX /data

# Debug stage for devcontainer/debugging only.
FROM build AS debug

WORKDIR /app

# Optional: only works if .git is copied into the build context.
# In production you should usually exclude .git using .dockerignore.
RUN if [ -d .git ]; then \
      git remote set-url origin git@github.com:yangjie500/sftp-watcher.git; \
    fi

# Make editable and debuggable.
RUN uv pip install debugpy
RUN uv pip install -e .

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Dev/debug paths.
ENV SFTP_WATCHER_DATABASE_DIR=/app/database
ENV SFTP_LOCAL_DIR=/app/watcher_local_directory

RUN mkdir -p /app/database /app/watcher_local_directory \
    && chmod -R o+rwX /app/database /app/watcher_local_directory

# Keep container alive so devcontainer can attach.
ENTRYPOINT ["/bin/bash", "-lc"]
CMD ["while true; do sleep 30; done"]

# Minimal production runtime.
FROM cgr.dev/chainguard/python:latest AS runtime

WORKDIR /app

# Copy only the ready-to-run virtualenv.
COPY --from=build --chown=65532:0 /app/.venv /app/.venv

# Copy prepared writable directory structure.
COPY --from=build --chown=65532:0 /data /data

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Runtime writable directories.
# In Helm, mount PVCs to these paths.
ENV SFTP_WATCHER_DATABASE_DIR=/data/database
ENV SFTP_LOCAL_DIR=/data/watcher_local_directory

# Chainguard Python uses /usr/bin/python as the default entrypoint,
# so we explicitly override it to use your installed CLI from the venv.
ENTRYPOINT ["sftp-watcher"]
CMD []
