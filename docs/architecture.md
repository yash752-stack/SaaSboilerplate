# Architecture Deep Dive

## System Overview

```mermaid
flowchart TD
    Browser["Browser / Frontend"] --> API["FastAPI app"]
    API --> Middleware["Middleware: request logging, CORS"]
    API --> Deps["Dependencies: auth, rate limits, org membership"]
    Deps --> Services["Service layer"]
    Services --> Models["SQLAlchemy models"]
    Models --> DB[("PostgreSQL / SQLite")]

    API --> Redis[("Redis")]
    Redis --> Celery["Celery workers"]
    Celery --> Email["Email tasks"]
    Celery --> Webhook["Webhook delivery"]
    Celery --> Maintenance["Maintenance / reminders"]

    Services --> Stripe["Stripe"]
    Services --> S3["S3-compatible storage"]
    API --> WS["WebSocket manager"]
```

## Why The Layers Exist

### `api/v1/endpoints/`

These files expose HTTP surfaces and should stay thin. They translate requests into service calls, manage dependency injection, and return response payloads.

### `services/`

Business logic lives here so Stripe, org management, analytics, audit logging, and notifications can evolve independently from transport concerns.

### `core/`

Shared runtime concerns such as settings, middleware, security, permissions, and rate limiting are centralized here to keep feature modules smaller and more predictable.

### `tasks/`

Anything that should not block a request path belongs in Celery tasks. This includes:

- email delivery
- outbound webhook delivery
- scheduled maintenance
- future retries or reporting jobs

## Auth Flow

```mermaid
sequenceDiagram
    participant User
    participant AuthAPI as /auth/*
    participant AuthService
    participant DB
    participant Redis

    User->>AuthAPI: Register or login
    AuthAPI->>AuthService: Validate payload
    AuthService->>DB: Persist or load user
    AuthService->>Redis: Store verification/reset/blacklist token state
    AuthService-->>User: Access + refresh tokens or verification flow response
```

## Tenant Access Flow

```mermaid
sequenceDiagram
    participant User
    participant Endpoint as /orgs/{org_id}/*
    participant Deps as get_current_org_membership
    participant DB

    User->>Endpoint: Request with JWT
    Endpoint->>Deps: Resolve current user + org_id
    Deps->>DB: Verify org exists and membership is active
    DB-->>Deps: Membership with role
    Deps-->>Endpoint: Allow or reject
    Endpoint-->>User: Tenant-scoped response
```

## Stripe Billing Flow

```mermaid
flowchart LR
    User["Authenticated user"] --> Checkout["Create checkout session"]
    Checkout --> Stripe["Stripe Checkout"]
    Stripe --> Webhook["/api/v1/billing/webhook"]
    Webhook --> Billing["billing_service"]
    Billing --> Subscription["Subscription + user plan sync"]
    Subscription --> Audit["Audit / analytics follow-up"]
```

## Realtime Notifications

```mermaid
flowchart LR
    Service["Service layer event"] --> Persist["Notification row"]
    Persist --> WS["WebSocket manager"]
    WS --> User["Connected user"]
```

## Async Philosophy

The boilerplate uses Celery because SaaS products accumulate slow, failure-prone, or retry-heavy work quickly. Background workers protect request latency and create a cleaner place for:

- retries
- backoff
- email sends
- outbound webhooks
- subscription reminder jobs

## Current Limits

- tenant context is enforced on organization routes, but future tenant-heavy modules should share a first-class tenant middleware
- observability is request-log and health-check oriented today, not full tracing
- WebSockets are in-process today, so horizontal scale would eventually benefit from shared pub/sub
