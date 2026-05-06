# Operations, Reliability, and Failure Handling

## Health Endpoints

The platform exposes three useful operational surfaces:

- `/api/v1/health` for a simple service-alive response
- `/api/v1/health/live` for liveness probes
- `/api/v1/health/ready` for readiness checks against the database and Redis

`/health/ready` returns `503` when dependencies are degraded so containers and orchestration layers can distinguish "process is running" from "service is ready."

## Logging

Implemented logging today includes:

- startup and shutdown events
- request IDs in logs and response headers
- per-request latency logging
- audit logs for admin, org, security, and webhook-sensitive actions

Recommended next evolution:

- JSON logs
- OpenTelemetry tracing
- Loki or ELK ingestion
- Prometheus request and worker metrics

## Failure Handling Notes

### Redis unavailable

Current behavior:

- request rate limiting fails open
- plan rate limiting fails open
- readiness endpoint reports degraded state

Why:

This keeps the core API reachable even if the control-plane helper system fails.

### Stripe webhook signature mismatch

Current behavior:

- request is rejected with `400`
- subscription state is not mutated

Why:

Billing events must be authenticated before any plan changes are applied.

### Celery worker unavailable

Current behavior:

- webhook dispatch attempts queueing
- if queue submission fails, delivery is marked as `queued_local_only`

Why:

This preserves operator visibility that a delivery was intended, even if it was not processed normally.

### Organization ownership safety

Current behavior:

- the last active org owner cannot be removed

Why:

Tenant resources should never become ownerless due to an admin mistake or API misuse.

## Security Notes

### Auth

- JWT access tokens protect API routes
- refresh tokens support longer sessions
- password reset and verification tokens are handled outside the access-token flow

### Account security

- TOTP-based 2FA is available
- API keys can be created and revoked
- admin routes require explicit admin role checks

### Data boundaries

- organization endpoints now require active membership checks
- org member administration requires `owner` or `admin`

### Input validation

- route payloads use Pydantic models
- Stripe webhooks verify signatures
- upload requests go through content-type and size rules before presigning

## Scaling Considerations

### API

- stateless API instances make horizontal scaling straightforward
- DB session management is already centralized

### Redis

- rate limiting and Celery brokering both depend on Redis
- a managed Redis deployment is recommended in production

### Database

- PostgreSQL is the intended production target
- SQLite remains useful for local demo and simple tests

### Workers

- queues can be scaled independently from the API
- heavy email or webhook bursts should not impact request latency

## Suggested Next Production Upgrades

- OpenTelemetry traces for API and workers
- Prometheus metrics for request throughput and queue depth
- dead-letter strategy for failed webhook deliveries
- idempotency keys for billing and webhook-heavy endpoints
- Terraform for reproducible deployment environments
