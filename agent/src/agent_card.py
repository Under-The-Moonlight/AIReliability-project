import os

from a2a.types import AgentCapabilities, AgentCard, AgentSkill


def build_agent_card() -> AgentCard:
    base_url = os.environ.get("AGENT_BASE_URL", "http://localhost:8080")
    return AgentCard(
        name="Kyverno Policy Generator",
        description=(
            "Generates Kyverno ClusterPolicy YAML manifests based on natural language "
            "requirements. Automatically checks whether a matching policy already exists "
            "in the cluster before generating a new one."
        ),
        url=f"{base_url}/",
        version="0.1.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="generate_kyverno_policy",
                name="Generate Kyverno Policy",
                description=(
                    "Generate a Kyverno ClusterPolicy YAML for a given security or "
                    "compliance requirement, or identify an existing policy that satisfies it."
                ),
                tags=["kyverno", "policy", "kubernetes", "security", "compliance"],
                examples=[
                    "Generate a policy that requires all pods to have resource limits",
                    "Create a policy to disallow privileged containers",
                    "Generate a policy that requires specific labels on all deployments",
                    "Create a policy that enforces read-only root filesystem",
                ],
            )
        ],
    )
