# AIReliability-project

## What Was Implemented

This repository deploys an AI reliability stack on Kubernetes using GitOps.

Tested environment: GitHub Codespaces, `kind`, and `cloud-provider-kind` as LB.

1. GitOps with Flux operator: Flux is bootstrapped using a `FluxInstance` and continuously reconciles this repository from `kubernetes/helmReleases`.
2. Secrets managed with Sealed Secrets: OpenAI credentials are stored as `SealedSecret` resources for both kagent and agentgateway so encrypted secrets can be safely versioned in Git. Each user should generate their own SealedSecrets for their cluster and credentials.
3. kagent with model configuration: kagent is deployed via HelmRelease, and `ModelConfig` uses model `gpt-4.1-mini` with `baseUrl` set to the in-cluster `agentgateway-proxy` endpoint.
4. Agent Gateway configured and reachable: agentgateway is deployed from OCI Helm charts, plus Gateway API resources (`Gateway` and `HTTPRoute`) are configured. The gateway endpoint is testable with the curl flow below, and kagent UI is accessible with:

```bash
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
```

5. Backend mapped to model path: an `AgentgatewayBackend` named `openai` is created, bound by `HTTPRoute`, and then consumed by kagent through the `ModelConfig` base URL.

## Environment Setup (Linux)

Follow these steps to prepare your environment and bootstrap the project.

### 1. Install kind and create a cluster

```bash
# For AMD64 / x86_64
[ $(uname -m) = x86_64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.31.0/kind-linux-amd64

# For ARM64
[ $(uname -m) = aarch64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.31.0/kind-linux-arm64

chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
kind create cluster
```

### 2. Install kubectl

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

### 3. Bootstrap FluxInstance

```bash
helm install flux-operator oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator \
	--namespace flux-system \
	--create-namespace

kubectl apply -f bootstrap/fluxinstance.yaml
```

### 4. Install kubeseal

```bash
KUBESEAL_VERSION=$(curl -s https://api.github.com/repos/bitnami-labs/sealed-secrets/tags | jq -r '.[0].name' | cut -c 2-)
curl -OL "https://github.com/bitnami-labs/sealed-secrets/releases/download/v${KUBESEAL_VERSION}/kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz"
tar -xvzf kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz kubeseal
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
```

### 5. Create a Sealed Secret

Generate this secret yourself (do not reuse another user's encrypted secret payload).

```bash
echo -n <API_KEY> | kubectl create secret generic mysecret --dry-run=client --from-file=apiKey=/dev/stdin -o yaml > mysecret.yaml
kubeseal -f mysecret.yaml -w kubernetes/helmReleases/kagent/kagentSecrets.yaml --controller-name sealed-secrets-controller --controller-namespace flux-system
```

### 6. Install cloud-provider-kind

```bash
wget https://github.com/kubernetes-sigs/cloud-provider-kind/releases/download/v0.10.0/cloud-provider-kind_0.10.0_linux_amd64.tar.gz
sudo tar -xvzf cloud-provider-kind_0.10.0_linux_amd64.tar.gz -C /go/bin
/go/bin/cloud-provider-kind >/dev/null 2>&1 &
```

If you need more LoadBalancer IPs, run this command again:

```bash
/go/bin/cloud-provider-kind >/dev/null 2>&1 &
```

### 7. Create a Sealed Secret for Agent Gateway

Generate this secret yourself as well, using your own API key.

```bash
echo -n <API_KEY> | kubectl create secret generic openai-secret -n agentgateway-system --dry-run=client --from-file=Authorization=/dev/stdin -o yaml > generatedAgentgatewaySecrets.yaml
kubeseal -f generatedAgentgatewaySecrets.yaml -w kubernetes/helmReleases/agentgateway/agentgatewaySecrets.yaml --controller-name sealed-secrets-controller --controller-namespace flux-system
```

### 8. Verify the Agent Gateway works

Use this as a quick smoke test after Flux finishes reconciling the resources.

You can also verify access to the UI and admin endpoints:

```bash
# kagent UI access
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
```

```bash
# agentgateway admin endpoint (forward the agentgateway-proxy workload)
kubectl port-forward -n agentgateway-system deploy/agentgateway-proxy 15000:15000
```

```bash
# Expose the in-cluster Agent Gateway proxy on localhost:9090.
# Keep this terminal running while you test the API.
kubectl port-forward -n agentgateway-system svc/agentgateway-proxy 9090:80
```

In another terminal, send a test chat completion request:

```bash
# Send a request through the local port-forward to confirm the gateway can reach the model backend.
curl -s http://localhost:9090/v1/chat/completions \
	-H "Content-Type: application/json" \
	-d '{
		"model": "gpt-4.1-mini",
		"messages": [{"role": "user", "content": "Hello!"}]
	}'
```

If everything is working, you should get a JSON response similar to this:

```json
{
	"model": "gpt-4.1-mini-2025-04-14",
	"usage": {
		"prompt_tokens": 9,
		"completion_tokens": 9,
		"total_tokens": 18
	},
	"choices": [
		{
			"message": {
				"content": "Hello! How can I assist you today?",
				"role": "assistant"
			},
			"finish_reason": "stop"
		}
	]
}
```

You can also test through the kagent UI end-to-end:

1. Open the kagent UI after port-forwarding `svc/kagent-ui`.
2. Create a new agent and choose model `agentgateway-gpt4-mini`.
3. Start chatting with that agent.
4. In another terminal, watch proxy logs while you chat:

```bash
kubectl logs -n agentgateway-system deploy/agentgateway-proxy -f
```

During the chat, you should see request logs from the agent traffic in `agentgateway-proxy`.

This confirms two things:

1. The `agentgateway-proxy` service is reachable.
2. The gateway can authenticate upstream and return a valid model response.

## Under Consideration

1. `kgateway` was added initially, but it currently behaves as an Envoy proxy layer for this setup, so it is disabled for now.
2. Verify whether credentials can be removed from `ModelConfig` and managed only in `AgentgatewayBackend` (current assumption).
