# T150 — T150 — Local DNS and reverse proxy for sandbox environments

**Source**: GitHub Issue #147

## Description

Goal: provide stable local URLs for sandbox environments using a generic reverse proxy and local DNS routing layer.

Context:
Sandbox environments currently rely on dynamically allocated localhost ports such as:
- localhost:3400
- localhost:8480

As persistent environments become first-class runtime targets, sandbox access should move toward stable local URLs.

Examples:
- https://sandbox-123.ai-dev-factory.localhost
- https://api.sandbox-123.ai-dev-factory.localhost
- https://project-x.localhost

Scope:
- introduce a generic local reverse proxy layer for sandbox environments
- support stable local hostnames instead of exposing raw ports to users
- route requests dynamically to sandbox web/API services
- support multiple concurrent sandbox environments
- automatically register sandbox routes during environment startup
- automatically unregister routes during cleanup
- keep routing generic and project-agnostic
- support future deploy.yml integration for declared public endpoints
- support local HTTPS when possible
- expose generated sandbox URLs in the dashboard UI

Potential implementation directions:
- Traefik
- Caddy
- nginx dynamic routing
- docker label-based routing
- local wildcard localhost domains

Tests:
- multiple concurrent sandbox hostnames
- route registration and cleanup
- API and web routing separation
- sandbox deletion removes routes
- persistent environments remain reachable after worker exit
- hostname collisions handled safely

Out of scope:
- internet/public exposure
- production ingress
- cloud DNS management
- authentication/SSO
- distributed routing

Acceptance:
- users can access sandbox environments via stable local hostnames instead of raw ports
- multiple sandbox environments can coexist simultaneously
- routes are automatically registered and cleaned up
- dashboard displays sandbox URLs
- routing remains generic and project-agnostic
