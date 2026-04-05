import os

import uvicorn
from a2a.server.agent_execution import AgentExecutor
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue, TaskArtifactUpdateEvent, TaskStatusUpdateEvent
from a2a.server.request_handlers import DefaultRequestHandler, RequestContext
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import Artifact, Message, Part, Role, TaskState, TaskStatus, TextPart
from opentelemetry import trace
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware

from src.agent import build_graph
from src.agent_card import build_agent_card
from src.tracing import setup_tracing

tracer = trace.get_tracer(__name__)


def _extract_text(message: Message) -> str:
    parts = []
    for part in message.parts:
        root = getattr(part, "root", part)
        if hasattr(root, "text"):
            parts.append(root.text)
    return " ".join(parts).strip()


class KyvernoPolicyExecutor(AgentExecutor):
    def __init__(self) -> None:
        self._graph = build_graph()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = _extract_text(context.message)

        with tracer.start_as_current_span("kyverno_policy_request") as span:
            span.set_attribute("user.request", user_text)

            event_queue.enqueue(
                TaskStatusUpdateEvent(
                    status=TaskStatus(
                        state=TaskState.working,
                        message=Message(
                            role=Role.agent,
                            parts=[
                                Part(
                                    root=TextPart(
                                        text="Checking existing Kyverno policies..."
                                    )
                                )
                            ],
                        ),
                    )
                )
            )

            state = await self._graph.ainvoke(
                {
                    "user_request": user_text,
                    "existing_policies": [],
                    "result": "",
                }
            )

            span.set_attribute(
                "policies.found", len(state.get("existing_policies", []))
            )

            event_queue.enqueue(
                TaskArtifactUpdateEvent(
                    artifact=Artifact(
                        parts=[Part(root=TextPart(text=state["result"]))]
                    )
                )
            )
            event_queue.enqueue(
                TaskStatusUpdateEvent(
                    status=TaskStatus(state=TaskState.completed)
                )
            )

        event_queue.close()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        event_queue.close()


def main() -> None:
    setup_tracing("kyverno-agent")

    handler = DefaultRequestHandler(
        agent_executor=KyvernoPolicyExecutor(),
        task_store=InMemoryTaskStore(),
    )

    app = A2AStarletteApplication(
        agent_card=build_agent_card(),
        http_handler=handler,
    ).build()

    app = OpenTelemetryMiddleware(app)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        log_level="info",
    )


if __name__ == "__main__":
    main()
