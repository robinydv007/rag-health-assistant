# Engineering Principles

> Guiding decisions throughout the project. When trade-offs arise, these resolve them.

## Core Principles

1. **One service, one job** — Each microservice does exactly one thing. No service owns two pipeline stages. Scope creep in a service is a design defect.

2. **Async by default, sync only at the edge** — Services communicate via SQS queues, not direct calls. The only synchronous boundary is the user-facing API. This is how we scale independently and survive partial failures.

3. **PII/PHI never travels downstream raw** — Patient data is scrubbed at the first point of file-content access (Doc Processing). Every downstream service operates on clean data. This is non-negotiable for HIPAA compliance.

4. **Zero downtime is a feature, not a luxury** — Knowledge base updates use shadow index + alias swap. Rolling deployments on ECS. Users never see an interruption.

5. **Observability is first-class** — Every service emits structured logs, metrics, and distributed traces from day one. An unobservable system is an unmanageable system.

6. **Queues control scaling** — Auto-scaling decisions are based on SQS queue depth, not CPU. Queue depth is the true signal of work pending; CPU is a lagging proxy.

7. **Admin is separated from user traffic** — The Admin service has elevated permissions (index alias writes, DLQ access). It never receives user traffic. Principle of least privilege at the service boundary.

8. **Fallback is a requirement, not an afterthought** — The LLM router has a circuit breaker that falls back to self-hosted Llama 2 / Mistral. If GPT-4/Claude go down, users still get answers. 99.9% uptime demands it.

9. **Ship incrementally** — each phase leaves the project in a deployable state with real value. No big-bang releases.

10. **Defer scope, not quality** — cut features before cutting correctness, safety, or compliance.

11. **Document decisions** — every significant architectural or design choice gets an ADR in `specs/decisions/`. The *why* matters as much as the *what*.

12. **Secrets never in code** — all credentials, API keys, and tokens come from environment variables or AWS Secrets Manager. Never committed to the repository.
