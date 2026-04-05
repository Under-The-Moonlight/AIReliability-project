import os

from phoenix.otel import register


def setup_tracing(service_name: str = "kyverno-agent") -> None:
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "")
    if not endpoint:
        return

    # Exclude readiness/liveness probe paths from tracing before auto-instrumentation runs
    excluded = "/.well-known/agent.json,/.well-known/agent-card.json"
    current = os.environ.get("OTEL_PYTHON_EXCLUDED_URLS", "")
    os.environ["OTEL_PYTHON_EXCLUDED_URLS"] = f"{current},{excluded}" if current else excluded

    register(
        project_name=service_name,
        endpoint=endpoint,
        protocol="grpc",
        auto_instrument=True,
        batch=True,
    )
