import os
from typing import Literal, TypedDict

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from .kyverno_client import apply_cluster_policy, list_cluster_policies

SYSTEM_PROMPT = """\
You are a Kyverno policy expert integrated into a Kubernetes cluster.

Decide how to respond based on the user request:

A) If the user is asking a general question (e.g. "what can you do?", "how does Kyverno work?",
   "list existing policies") — answer conversationally in plain text. Do NOT output YAML.

B) If the user asks to CREATE or GENERATE a policy:
   - Check existing policies (provided below). If one already covers the request, reply:
     "A matching policy already exists: <policy-name>"
   - Otherwise output EXACTLY a fenced YAML code block (```yaml ... ```) containing a complete,
     valid Kyverno ClusterPolicy manifest. Nothing before or after the code block.
     Rules:
       * apiVersion: kyverno.io/v1
       * kind: ClusterPolicy
       * descriptive metadata.name in kebab-case
       * spec.rules with at least one rule

Always keep answers concise.
"""


class PolicyState(TypedDict):
    user_request: str
    existing_policies: list[dict]
    llm_response: str
    result: str


def _make_llm() -> object:
    return ChatOpenAI(
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.environ.get("OPENAI_API_KEY", "dummy"),
        model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
    )


def fetch_policies(state: PolicyState) -> dict:
    cluster_policies = list_cluster_policies()
    return {"existing_policies": cluster_policies}


def generate_response(state: PolicyState) -> dict:
    llm = _make_llm()

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
    return {"llm_response": response.content}


def _extract_yaml(text: str) -> str | None:
    """Extract YAML from a fenced code block, or return None."""
    import re
    match = re.search(r"```(?:yaml)?\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def apply_or_return(state: PolicyState) -> dict:
    """If the LLM produced a YAML policy, apply it to the cluster."""
    raw = state["llm_response"]
    yaml_str = _extract_yaml(raw)

    if yaml_str is None:
        # Conversational answer or "already exists" message — return as-is
        return {"result": raw}

    try:
        policy_body = yaml.safe_load(yaml_str)
        name = apply_cluster_policy(policy_body)
        return {"result": f"Policy **{name}** has been created/updated in the cluster.\n\n```yaml\n{yaml_str}\n```"}
    except Exception as e:
        # Cluster not available or error — still return the YAML so user can apply manually
        return {"result": f"Generated policy (could not apply automatically: {e}):\n\n```yaml\n{yaml_str}\n```"}


def build_graph():
    graph = StateGraph(PolicyState)
    graph.add_node("fetch_policies", fetch_policies)
    graph.add_node("generate_response", generate_response)
    graph.add_node("apply_or_return", apply_or_return)
    graph.add_edge(START, "fetch_policies")
    graph.add_edge("fetch_policies", "generate_response")
    graph.add_edge("generate_response", "apply_or_return")
    graph.add_edge("apply_or_return", END)
    return graph.compile()
