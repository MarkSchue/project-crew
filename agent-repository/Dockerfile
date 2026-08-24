# Control-plane container (plan milestone M6.4, ADR-004).

# The control plane runs separately from the execution plane; it is the
# only process with registry/policy/schema access. Build:
#
#   docker build -f Dockerfile -t agent-platform-control .
#
# Run:
#
#   docker run -p 8000:8000 -e AGENT_PLATFORM_ADMIN_TOKEN=... agent-platform-control

FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir -e .

COPY src/ ./src/
COPY tools/ ./tools/
COPY registry/ ./registry/

ENV AGENT_PLATFORM_REGISTRY_DIR=/app/registry
EXPOSE 8000

CMD ["uvicorn", "agent_platform.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
