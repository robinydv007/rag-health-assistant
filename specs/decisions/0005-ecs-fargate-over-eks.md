# ADR 0005 — ECS Fargate Over EKS for Container Orchestration

> **Status**: accepted
> **Date**: 2026-05-12
> **Supersedes**: N/A

## Context

The system requires container orchestration for 5 of the 6 services (Chat, Uploader, Doc Processing, Indexing, Admin — all CPU-based). The Embedding Service runs on EC2 GPU, managed separately.

Two primary AWS options:

- **ECS Fargate**: Fully managed serverless containers. AWS manages the control plane and worker nodes. Define task definitions; Fargate runs them.
- **EKS (Kubernetes)**: Managed Kubernetes. AWS manages the control plane; we manage worker nodes (or use Fargate with EKS, which adds complexity).

The team is a backend engineering team — strong Python/ML skills, not Kubernetes operations specialists. The 99.9% uptime requirement is high, but the failure modes are application-level (service crashes, queue failures), not infrastructure-level (node failure, etcd quorum loss).

## Decision

Use **AWS ECS Fargate** for all CPU-based services.

Auto-scaling via Application Auto Scaling triggered by CloudWatch metrics:
- Chat Service: scale on ALB ActiveConnectionCount
- Uploader: scale on RequestCount
- Doc Processing / Indexing: scale on SQS queue depth (ApproximateNumberOfMessagesVisible)
- Admin: fixed at 2 tasks (minimal load)

## Consequences

### Positive
- No cluster to manage — no worker node patching, no etcd, no kubelet tuning
- Auto-scaling integration with CloudWatch and SQS is native and well-documented
- Simpler operational model: ECS task definitions + service definitions, not Kubernetes YAML
- Faster time to production: no Kubernetes expertise required
- Cost: no EC2 worker nodes to pay for when traffic is low; Fargate bills by vCPU-second

### Negative
- Less flexibility than Kubernetes for complex networking, custom schedulers, or advanced deployment strategies
- No native support for sidecar patterns like Istio service mesh (not needed for this system)
- ECS Fargate has higher per-task CPU/memory cost than self-managed EC2 at large scale (tradeoff: no ops burden)

### Risks
- If the system grows to require Kubernetes features (multi-cluster, custom operators, complex affinity rules), migration from ECS to EKS is significant work. Mitigation: the architecture is designed around standard container/queue patterns that migrate cleanly.

## Alternatives Considered

| Option | Why Rejected |
|--------|-------------|
| EKS (self-managed nodes) | Requires Kubernetes expertise; worker node management; patching burden; overkill for this team size |
| EKS Fargate | Adds EKS control plane cost + complexity without meaningful gains over ECS Fargate for this use case |
| EC2 Auto Scaling Group | More control but significantly more operational burden; no serverless billing |
| AWS Lambda | Cold start incompatible with p95 < 2s for Chat Service; 15-min timeout incompatible with long doc processing; no GPU |
