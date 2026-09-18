# Starcloud Integration

`starcloud_integration` is an independent Frappe app that provides the ERPNext Desk boundary for Starcloud administration.

## Scope

- The browser calls named Frappe whitelist methods only.
- Frappe forwards restricted requests to Starcloud `/api/erpnext/*` endpoints.
- Starcloud remains the owner of application data and review state transitions.
- The browser never receives the upstream shared secret or application `client_secret`.
- `Starcloud User` has read-only access; `Starcloud Admin` and `System Manager` can review applications.

## Site Configuration

Set these values in the target Frappe site configuration. Do not commit secrets to Git or bake them into an image.

```json
{
  "starcloud_api_base_url": "https://cloud.skychip.top",
  "starcloud_api_timeout_seconds": 10,
  "starcloud_health_path": "/api/erpnext/health",
  "starcloud_proxy_shared_secret": "set-in-site-config"
}
```

`starcloud_proxy_shared_secret` must match `ERPNEXT_PROXY_SHARED_SECRET` in the Starcloud runtime environment. It must be different from the Starcompany proxy secret.

## Local Validation

```bash
python -m compileall starcloud_integration
node --check starcloud_integration/starcloud/page/starcloud_applications/starcloud_applications.js
```

## Installation

Build this app into the ERPNext v16 image, then install it only on the intended site:

```bash
bench --site erp.skychip.top install-app starcloud_integration
bench --site erp.skychip.top migrate
bench --site erp.skychip.top clear-cache
```

Assign `Starcloud User` for read-only access or `Starcloud Admin` for approval and rejection. `System Manager` remains the fallback administrator role.