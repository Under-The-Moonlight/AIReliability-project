from kubernetes import client, config
from kubernetes.client.exceptions import ApiException


class _NoConfigError(Exception):
    pass


def _load_config() -> None:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        try:
            config.load_kube_config()
        except config.ConfigException:
            raise _NoConfigError("No Kubernetes configuration found")


def list_cluster_policies() -> list[dict]:
    try:
        _load_config()
    except _NoConfigError:
        return []
    api = client.CustomObjectsApi()
    try:
        result = api.list_cluster_custom_object(
            group="kyverno.io",
            version="v1",
            plural="clusterpolicies",
        )
        return [
            {"name": item["metadata"]["name"], "kind": "ClusterPolicy"}
            for item in result.get("items", [])
        ]
    except ApiException as e:
        if e.status == 404:
            return []
        raise


def apply_cluster_policy(policy_body: dict) -> str:
    """Create or update a ClusterPolicy. Returns the policy name."""
    _load_config()
    api = client.CustomObjectsApi()
    name = policy_body["metadata"]["name"]
    try:
        api.create_cluster_custom_object(
            group="kyverno.io",
            version="v1",
            plural="clusterpolicies",
            body=policy_body,
        )
    except ApiException as e:
        if e.status == 409:
            # Already exists — patch it
            api.patch_cluster_custom_object(
                group="kyverno.io",
                version="v1",
                plural="clusterpolicies",
                name=name,
                body=policy_body,
            )
        else:
            raise
    return name
