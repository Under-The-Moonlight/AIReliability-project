# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **GitOps-based Kubernetes deployment** for an AI reliability stack. There are no traditional build artifacts — all "code" is Kubernetes/Helm YAML that Flux CD continuously reconciles into a cluster.

## Cluster Operations

### Bootstrap (first-time setup)

```bash
# Install Flux operator
helm install flux-operator oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator \
  --namespace flux-system --create-namespace

# Seal an OpenAI API key (repeat per namespace: kagent, agentgateway-system)
echo -n "sk-..." | kubectl create secret generic openai-api-key \
  --namespace kagent --from-file=apiKey=/dev/stdin --dry-run=client -o yaml \
  | kubeseal -o yaml > kubernetes/kagent/resources/openai-api-key-sealed.yaml

# Trigger GitOps reconciliation
kubectl apply -f bootstrap/fluxinstance.yaml
```

### Day-to-day operations

```bash
# Force Flux to reconcile immediately (instead of waiting up to 5 min)
flux reconcile kustomization cluster --with-source

# Watch reconciliation status
flux get kustomizations --watch

# Access kagent UI
kubectl port-forward -n kagent svc/kagent-ui 8080:80

# Access agentgateway proxy
kubectl port-forward -n agentgateway-system svc/agentgateway-proxy 9090:80

# Access Phoenix observability UI
kubectl port-forward -n phoenix svc/phoenix-server 6006:6006

# Test end-to-end
curl http://localhost:9090/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4.1-mini","messages":[{"role":"user","content":"hello"}]}'
```

## Architecture

```
Git repo (this repo)
    └── Flux CD (watches kubernetes/cluster/, 5-min interval)
            ├── kagent-core  →  kagent-resources  →  mcp  →  agents
            ├── agentgateway-core  →  agentgateway-resources
            ├── gateway (Gateway API CRDs)
            └── phoenix (observability)
```

**Request path**: User → agentgateway-proxy (port 80) → HTTPRoute → AgentgatewayBackend → OpenAI API

**AI agent path**: sre-expert Agent → ModelConfig (baseUrl: agentgateway-proxy) → agentgateway → OpenAI

**Tracing path**: kagent → OTLP (port 4317) → Phoenix

### Key namespaces

| Namespace | Contents |
|---|---|
| `flux-system` | Flux controllers, FluxInstance, Kustomizations |
| `kagent` | kagent controller, sre-expert agent, MCP servers, ModelConfig |
| `agentgateway-system` | agentgateway proxy, Gateway, HTTPRoute, Backend |
| `phoenix` | Phoenix observability server |

### Dependency order

Flux enforces this `dependsOn` chain — changes to earlier steps must reconcile before later steps proceed:

1. `cluster` (root)
2. `kagent-core` + `agentgateway-core` + `gateway` + `phoenix` (parallel)
3. `kagent-resources` + `agentgateway-resources` (depend on their respective cores)
4. `mcp` (depends on `kagent-core`)
5. `agents` (depends on `kagent-resources` + `mcp`)

### Secrets

All secrets are encrypted via Sealed Secrets (controller in `flux-system`). Raw secret values are **never committed**. To rotate a secret, re-seal it with `kubeseal` and commit the updated `*-sealed.yaml` file.

## Directory Structure

```
bootstrap/          # One-time FluxInstance bootstrap manifest
kubernetes/
  cluster/          # Flux Kustomization orchestration layer (entry point)
  agentgateway/     # agentgateway HelmRelease + CRDs + Backend/Route resources
  kagent/           # kagent HelmRelease + CRDs + ModelConfig + SealedSecrets
  agents/           # Declarative Agent CRs (sre-expert)
  mcp/              # MCP server deployments (k8s tools, web-fetch)
  gateway/          # Gateway API CRD HelmRelease
  phoenix/          # Phoenix HelmRelease
```

## Making Changes

Since this is GitOps, the workflow is always: **edit YAML → commit → push → Flux reconciles**.

- Helm chart versions are pinned in `HelmRelease` resources under each component directory.
- To upgrade a chart, update the `spec.chart.spec.version` field and push.
- Flux `ArtifactGenerator` in `kubernetes/cluster/artifacts.yaml` defines the 7 artifact streams — add new components there first.
- New namespaced secrets must be sealed against the cluster's public key before committing.
