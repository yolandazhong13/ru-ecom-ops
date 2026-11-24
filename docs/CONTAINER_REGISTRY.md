# Container Registry Configuration Guide
## Supporting multiple container registry providers for ru-ecom-ops

## 1. Docker Hub Configuration

### Prerequisites
- Docker Hub account: https://hub.docker.com
- Access token created in account settings

### Setup Steps

```bash
# Login to Docker Hub
docker login -u your-username

# Tag image
docker tag ru-ecom-ops:latest your-username/ru-ecom-ops:latest
docker tag ru-ecom-ops:latest your-username/ru-ecom-ops:v1.0.0

# Push to Docker Hub
docker push your-username/ru-ecom-ops:latest
docker push your-username/ru-ecom-ops:v1.0.0

# In Kubernetes, create image pull secret
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=docker.io \
  --docker-username=your-username \
  --docker-password=your-access-token \
  --docker-email=your-email@example.com \
  -n ru-ecom-ops
```

### In deployment.yaml
```yaml
spec:
  template:
    spec:
      imagePullSecrets:
        - name: dockerhub-secret
      containers:
        - image: your-username/ru-ecom-ops:latest
```

---

## 2. GitHub Container Registry (GHCR) Configuration

### Prerequisites
- GitHub account with repository
- Personal Access Token with `write:packages` scope

### Setup Steps

```bash
# Login to GHCR
export CR_PAT=your-personal-access-token
echo $CR_PAT | docker login ghcr.io -u username --password-stdin

# Tag image with GHCR format
docker tag ru-ecom-ops:latest ghcr.io/your-org/ru-ecom-ops:latest
docker tag ru-ecom-ops:latest ghcr.io/your-org/ru-ecom-ops:v1.0.0

# Push to GHCR
docker push ghcr.io/your-org/ru-ecom-ops:latest
docker push ghcr.io/your-org/ru-ecom-ops:v1.0.0

# In Kubernetes, create image pull secret
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=your-username \
  --docker-password=your-personal-access-token \
  --docker-email=your-email@example.com \
  -n ru-ecom-ops
```

### In deployment.yaml
```yaml
spec:
  template:
    spec:
      imagePullSecrets:
        - name: ghcr-secret
      containers:
        - image: ghcr.io/your-org/ru-ecom-ops:latest
```

---

## 3. Amazon ECR Configuration

### Prerequisites
- AWS Account with ECR access
- AWS CLI configured with credentials
- IAM permissions: `ecr:*`

### Setup Steps

```bash
# Create ECR repository
aws ecr create-repository \
  --repository-name ru-ecom-ops \
  --region us-east-1 \
  --image-tag-mutability MUTABLE \
  --image-scanning-configuration scanOnPush=true

# Get login token and login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789.dkr.ecr.us-east-1.amazonaws.com

# Tag image with ECR format
docker tag ru-ecom-ops:latest \
  123456789.dkr.ecr.us-east-1.amazonaws.com/ru-ecom-ops:latest
docker tag ru-ecom-ops:latest \
  123456789.dkr.ecr.us-east-1.amazonaws.com/ru-ecom-ops:v1.0.0

# Push to ECR
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/ru-ecom-ops:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/ru-ecom-ops:v1.0.0

# Create Kubernetes secret for ECR
aws ecr get-login-password --region us-east-1 | \
  kubectl create secret docker-registry ecr-secret \
  --docker-server=123456789.dkr.ecr.us-east-1.amazonaws.com \
  --docker-username=AWS \
  --docker-password=$(aws ecr get-login-password --region us-east-1) \
  --docker-email=example@example.com \
  -n ru-ecom-ops
```

### In deployment.yaml
```yaml
spec:
  template:
    spec:
      imagePullSecrets:
        - name: ecr-secret
      containers:
        - image: 123456789.dkr.ecr.us-east-1.amazonaws.com/ru-ecom-ops:latest
```

---

## 4. Google Container Registry (GCR) Configuration

### Prerequisites
- Google Cloud Project
- Service Account with `storage.admin` role
- gcloud CLI configured

### Setup Steps

```bash
# Create service account for Docker authentication
gcloud iam service-accounts create docker-push \
  --display-name="Docker push account"

# Grant permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=serviceAccount:docker-push@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/storage.admin

# Create and download key
gcloud iam service-accounts keys create key.json \
  --iam-account=docker-push@PROJECT_ID.iam.gserviceaccount.com

# Configure docker authentication
cat key.json | docker login -u _json_key --password-stdin \
  https://gcr.io

# Tag image with GCR format
docker tag ru-ecom-ops:latest gcr.io/PROJECT_ID/ru-ecom-ops:latest
docker tag ru-ecom-ops:latest gcr.io/PROJECT_ID/ru-ecom-ops:v1.0.0

# Push to GCR
docker push gcr.io/PROJECT_ID/ru-ecom-ops:latest
docker push gcr.io/PROJECT_ID/ru-ecom-ops:v1.0.0

# Create Kubernetes secret for GCR
kubectl create secret docker-registry gcr-secret \
  --docker-server=gcr.io \
  --docker-username=_json_key \
  --docker-password="$(cat key.json)" \
  --docker-email=example@example.com \
  -n ru-ecom-ops
```

### In deployment.yaml
```yaml
spec:
  template:
    spec:
      imagePullSecrets:
        - name: gcr-secret
      containers:
        - image: gcr.io/PROJECT_ID/ru-ecom-ops:latest
```

---

## 5. Azure Container Registry (ACR) Configuration

### Prerequisites
- Azure Subscription
- Azure CLI configured
- Container Registry created

### Setup Steps

```bash
# Create Azure Container Registry
az acr create \
  --resource-group myResourceGroup \
  --name myregistry \
  --sku Basic

# Get registry URL
az acr show \
  --resource-group myResourceGroup \
  --name myregistry \
  --query loginServer --output tsv

# Login to ACR
az acr login --name myregistry

# Tag image with ACR format
docker tag ru-ecom-ops:latest \
  myregistry.azurecr.io/ru-ecom-ops:latest
docker tag ru-ecom-ops:latest \
  myregistry.azurecr.io/ru-ecom-ops:v1.0.0

# Push to ACR
docker push myregistry.azurecr.io/ru-ecom-ops:latest
docker push myregistry.azurecr.io/ru-ecom-ops:v1.0.0

# Create service principal for Kubernetes
az ad sp create-for-rbac \
  --name ru-ecom-ops-sp \
  --role acrpull \
  --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.ContainerRegistry/registries/{registry-name}

# Create Kubernetes secret for ACR
kubectl create secret docker-registry acr-secret \
  --docker-server=myregistry.azurecr.io \
  --docker-username=<appId> \
  --docker-password=<password> \
  --docker-email=example@example.com \
  -n ru-ecom-ops
```

### In deployment.yaml
```yaml
spec:
  template:
    spec:
      imagePullSecrets:
        - name: acr-secret
      containers:
        - image: myregistry.azurecr.io/ru-ecom-ops:latest
```

---

## Registry Comparison

| Registry | Cost | Ease | Private | Auto-scanning | CI/CD Integration |
|----------|------|------|---------|---------------|-------------------|
| Docker Hub | Free tier available | Very easy | Yes | No | Good (via Actions) |
| GHCR | Free (GitHub) | Easy | Yes (private repos) | Yes | Excellent |
| ECR | Per-storage/transfer | Medium | Yes | Yes | Excellent (AWS) |
| GCR | Per-storage/transfer | Medium | Yes | Yes | Excellent (GCP) |
| ACR | Per-registry | Medium | Yes | Yes | Excellent (Azure) |

---

## Best Practices

### 1. Image Tagging Strategy
```bash
# Use semantic versioning
docker tag ru-ecom-ops:latest registry/ru-ecom-ops:v1.0.0
docker tag ru-ecom-ops:latest registry/ru-ecom-ops:v1.0
docker tag ru-ecom-ops:latest registry/ru-ecom-ops:latest

# Use commit SHA for traceability
docker tag ru-ecom-ops:latest registry/ru-ecom-ops:sha-abc123def

# Use branch names for CI/CD
docker tag ru-ecom-ops:latest registry/ru-ecom-ops:main
docker tag ru-ecom-ops:latest registry/ru-ecom-ops:staging
```

### 2. Image Security
- Scan images for vulnerabilities: `docker scan ru-ecom-ops`
- Use minimal base images: Alpine, Distroless
- Keep base images updated
- Sign images with Docker Content Trust

### 3. Registry Authentication
- Use service accounts, not personal credentials
- Rotate access tokens regularly
- Restrict permissions to minimum required
- Use separate credentials for each environment

### 4. Garbage Collection
```bash
# Docker Hub - delete old images manually or via API
# ECR - set lifecycle policies
aws ecr put-lifecycle-policy \
  --repository-name ru-ecom-ops \
  --lifecycle-policy-text file://lifecycle.json

# GCR - set retention policies
# ACR - use lifecycle management policies
```

---

## Troubleshooting

### "Authentication required" error
```bash
# Re-login to registry
docker logout registry.example.com
docker login registry.example.com

# Update Kubernetes secret
kubectl delete secret image-pull-secret -n ru-ecom-ops
kubectl create secret docker-registry image-pull-secret \
  --docker-server=registry.example.com \
  --docker-username=username \
  --docker-password=password \
  -n ru-ecom-ops
```

### Image not found error
```bash
# Verify image exists
docker images | grep ru-ecom-ops

# Check registry for image
aws ecr describe-images --repository-name ru-ecom-ops

# Verify deployment references correct image
kubectl get deployment -n ru-ecom-ops -o jsonpath='{.items[0].spec.template.spec.containers[0].image}'
```

### Slow image pulls
- Use image caching in CI/CD
- Use regional registries
- Pre-pull images to nodes: `kubectl apply -f image-preloader.yaml`
