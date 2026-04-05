import os
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from .kyverno_client import list_cluster_policies, list_namespaced_policies

SYSTEM_PROMPT = """\
You are a Kyverno policy expert. You help users generate Kyverno ClusterPolicy YAML manifests.

When given a user request and the list of existing policy names already in the cluster:
1. If an existing policy clearly covers the request, respond with:
   "A matching policy already exists: <policy-name>"
2. Otherwise, generate a complete, valid Kyverno ClusterPolicy YAML manifest.

Rules for generated policies:
- Use apiVersion: kyverno.io/v1
- Use kind: ClusterPolicy
- Include a descriptive metadata.name (kebab-case)
- Include spec.rules with at least one rule
- Return only the YAML, no extra explanation
"""


class PolicyState(TypedDict):
    user_request: str
    existing_policies: list[dict]
    result: str


def fetch_policies(state: PolicyState) -> dict:
    cluster_policies = list_cluster_policies()
    return {"existing_policies": cluster_policies}


def generate_or_find_policy(state: PolicyState) -> dict:
    llm = ChatOpenAI(
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.environ.get("OPENAI_API_KEY", "dummy"),
        model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
    )

    policy_names = [p["name"] for p in state["existing_policies"]]
    existing_summary = (
        f"Existing ClusterPolicies: {', '.join(policy_names)}"
        if policy_names
        else "No existing ClusterPolicies found."
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=f"{existing_summary}\n\nUser request: {state['user_request']}"
        ),
    ]

    response = llm.invoke(messages)
    return {"result": response.content}


def build_graph():
    graph = StateGraph(PolicyState)
    graph.add_node("fetch_policies", fetch_policies)
    graph.add_node("generate_or_find_policy", generate_or_find_policy)
    graph.add_edge(START, "fetch_policies")
    graph.add_edge("fetch_policies", "generate_or_find_policy")
    graph.add_edge("generate_or_find_policy", END)
    return graph.compile()
