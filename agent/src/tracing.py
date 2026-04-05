import os

from phoenix.otel import register


def setup_tracing(service_name: str = "kyverno-agent") -> None:
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "")
    if not endpoint:
        return

    register(
        project_name=service_name,
        endpoint=endpoint,
        protocol="grpc",
        auto_instrument=True,  # instruments LangGraph and OpenAI automatically
        batch=True,
    )
