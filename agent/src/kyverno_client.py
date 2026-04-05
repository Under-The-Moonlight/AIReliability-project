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
            # No cluster available (e.g. local dev without kubeconfig)
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
            # Kyverno CRDs not installed yet
            return []
        raise


def list_namespaced_policies(namespace: str = "default") -> list[dict]:
    try:
        _load_config()
    except _NoConfigError:
        return []
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
