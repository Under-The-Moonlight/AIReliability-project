from kubernetes import client, config
from kubernetes.client.exceptions import ApiException


def _load_config() -> None:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


def list_cluster_policies() -> list[dict]:
    _load_config()
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
            # Kyverno CRDs not installed yet
            return []
        raise


def list_namespaced_policies(namespace: str = "default") -> list[dict]:
    _load_config()
    api = client.CustomObjectsApi()
    try:
        result = api.list_namespaced_custom_object(
            group="kyverno.io",
            version="v1",
            namespace=namespace,
            plural="policies",
        )
        return [
            {"name": item["metadata"]["name"], "namespace": namespace, "kind": "Policy"}
            for item in result.get("items", [])
        ]
    except ApiException as e:
        if e.status == 404:
            return []
        raise
