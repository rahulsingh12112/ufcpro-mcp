# ufcpro.in MCP Server

An MCP (Model Context Protocol) server that exposes the ufcpro.in job-search
engine as tools, resources, and prompts, consumable by any MCP-compatible host
(Claude Desktop, Cursor, or a custom client). It ships with a Bedrock Claude
client, a web chat UI secured by AWS Cognito, and an end-to-end GitOps delivery
pipeline on EKS.

## Architecture

```
Browser (job.ufcpro.in)
   │  Cognito OAuth2 login
   ▼
CloudFront + WAF ──► ALB ──► EKS pod
                              ├── chat_app.py  (Flask: host + MCP client)
                              └── mcp_server.py (MCP server, stdio subprocess)
                                      │
                                      ├── Bedrock Claude   (tool-use loop)
                                      └── ufcpro.in/api/jobs (live job data)
```

## Components

| File | Purpose |
|------|---------|
| `mcp_server.py` | MCP server: tools (`find_jobs`, `match_jd`), resources (resume skills, job sources), prompt (`outreach_email`) |
| `mcp_client.py` | Reference client using the raw Bedrock Converse API |
| `mcp_client_langchain.py` | Client using `langchain-mcp-adapters` + a ReAct agent |
| `chat_app.py` | Flask backend: web chat UI, Cognito auth gate, MCP client |
| `auth.py` | Cognito OAuth2 (authorization-code) login and JWT verification |
| `chat.html` | Chat front-end |
| `deploy/terraform/` | ECR repository, IAM role, EKS Pod Identity association |
| `deploy/helm/` | Deployment, Service, Ingress, HPA, ServiceAccount |
| `deploy/argocd/` | ArgoCD Application (GitOps) |
| `deploy/policy/` | OPA/conftest security policies |
| `.gitlab-ci.yml` | CI/CD pipeline (one-click deploy) |

## Tools, resources, and prompts

- **Tools** (model-invoked): `find_jobs(category)`, `match_jd(jd_text, category)`
- **Resources** (read-only): `resume://{category}/skills`, `config://job-sources`
- **Prompt** (user-selected): `outreach_email(company, role, your_name)`

## Local development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Inspect the server
npx @modelcontextprotocol/inspector python mcp_server.py

# Run a client (requires AWS credentials with Bedrock access)
python mcp_client_langchain.py "Find top 3 devops jobs in India"

# Run the web chat UI
export COGNITO_CLIENT_SECRET=<cognito app client secret>
python chat_app.py        # http://localhost:8800
```

## Configuration

| Variable | Description |
|----------|-------------|
| `AWS_REGION` | AWS region (default `us-east-1`) |
| `MCP_MODEL` | Bedrock model/inference-profile ID |
| `UFCPRO_BASE` | Job API base URL (default `https://ufcpro.in`) |
| `COGNITO_POOL_ID` | Cognito user pool ID |
| `COGNITO_CLIENT_ID` | Cognito app client ID |
| `COGNITO_CLIENT_SECRET` | Cognito app client secret (never commit) |
| `COGNITO_DOMAIN` | Cognito hosted domain |
| `COGNITO_REDIRECT_URI` | OAuth callback URL |
| `FLASK_SECRET` | Flask session secret |

Secrets are provided at runtime via environment variables locally and via a
Kubernetes Secret in production. They are never stored in Git.

## Deployment

Infrastructure is provisioned with Terraform and delivered to EKS via GitOps.

```bash
# 1. Provision ECR, IAM role, and the Pod Identity association
cd deploy/terraform
terraform init
terraform apply

# 2. Create the application namespace and secrets
kubectl create namespace ufcpro
kubectl -n ufcpro create secret generic ufcpro-mcp-secrets \
  --from-literal=COGNITO_CLIENT_SECRET=<secret> \
  --from-literal=FLASK_SECRET=$(openssl rand -hex 32)

# 3. Register the ArgoCD application
kubectl apply -f deploy/argocd/application.yaml
```

Thereafter, pushing to `main` and triggering the pipeline builds the image,
pushes it to ECR, updates the image tag in Git, and ArgoCD syncs it to the
cluster.

## CI/CD pipeline

Triggered by the manual `start-deploy` job, the pipeline runs end to end:

1. **validate** — `terraform validate`, `helm lint`
2. **security** — tfsec, Checkov, OPA/conftest, Trivy (filesystem)
3. **infra** — `terraform apply`
4. **build** — build and push the image to ECR
5. **scan-image** — Trivy image scan (fails on HIGH/CRITICAL CVEs)
6. **package** — package and push the Helm chart to ECR (OCI)
7. **release** — bump the image tag in Git (GitOps source of truth)
8. **deploy** — ArgoCD syncs and waits for a healthy rollout
9. **smoke-test** — verifies the live site responds and the auth gate is enforced
10. **done** — prints the live URL

Required CI/CD variables: `AWS_ACCOUNT_ID`, `AWS_CI_ROLE_ARN`,
`GITLAB_DEPLOY_TOKEN`, `ARGOCD_SERVER`, `ARGOCD_USER`, `ARGOCD_PASSWORD`.

## Security

- Authentication and authorization via AWS Cognito (OAuth2); tokens verified
  against Cognito's JWKS.
- Pod credentials via EKS Pod Identity (no static keys).
- Secrets held in a Kubernetes Secret, injected as environment variables.
- Shift-left scanning in CI: IaC (tfsec, Checkov), policy-as-code (OPA),
  and image/dependency CVEs (Trivy).
