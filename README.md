# AIReliability-project

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