import os

from phoenix.otel import register


def setup_tracing(service_name: str = "kyverno-agent") -> None:
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "")
    if not endpoint:
        return

    # auto_instrument=True would also trace every HTTP request including
    # readiness/liveness probes. Disable it and instrument only the
    # libraries we care about (LangChain/LangGraph and OpenAI).
    tracer_provider = register(
        project_name=service_name,
        endpoint=endpoint,
        protocol="grpc",
        auto_instrument=False,
        batch=True,
    )

    from openinference.instrumentation.langchain import LangChainInstrumentor
    from openinference.instrumentation.openai import OpenAIInstrumentor

    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
