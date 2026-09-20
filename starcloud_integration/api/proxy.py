import json
import logging
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import frappe
from frappe import _


VIEW_ROLES = {"Starcloud User", "Starcloud Admin", "System Manager"}
REVIEW_ROLES = {"Starcloud Admin", "System Manager"}


class StarcloudProxyError(frappe.ValidationError):
    pass


def _roles():
    if frappe.session.user == "Guest":
        frappe.throw(_("Login is required."), frappe.AuthenticationError)
    return set(frappe.get_roles(frappe.session.user))


def _require_access():
    if not VIEW_ROLES.intersection(_roles()):
        frappe.throw(_("You do not have permission to access Starcloud."), frappe.PermissionError)


def _require_review():
    if not REVIEW_ROLES.intersection(_roles()):
        frappe.throw(_("You do not have permission to review Starcloud applications."), frappe.PermissionError)


def _positive_int(value, label):
    try:
        value = int(value)
    except (TypeError, ValueError):
        frappe.throw(_("{0} must be an integer.").format(label), StarcloudProxyError)
    if value < 1:
        frappe.throw(_("Invalid {0}.").format(label), StarcloudProxyError)
    return value


def _settings():
    base_url = (frappe.conf.get("starcloud_api_base_url") or "").rstrip("/")
    timeout = int(frappe.conf.get("starcloud_api_timeout_seconds") or 10)
    shared_secret = frappe.conf.get("starcloud_proxy_shared_secret") or ""
    if not base_url or not shared_secret:
        frappe.throw(_("Starcloud proxy is not configured."), StarcloudProxyError)
    if timeout < 1 or timeout > 60:
        frappe.throw(_("Starcloud API timeout must be between 1 and 60 seconds."), StarcloudProxyError)
    return base_url, timeout, shared_secret


def _request_id():
    if getattr(frappe.local, "request", None):
        return frappe.get_request_header("X-Request-ID") or str(uuid.uuid4())
    return str(uuid.uuid4())


def _context(request_id):
    user = frappe.get_doc("User", frappe.session.user)
    return {
        "request_id": request_id,
        "erpnext_user": user.name,
        "email": user.email or "",
        "full_name": user.full_name or "",
        "roles": frappe.get_roles(user.name),
        "keycloak_sub": user.get("keycloak_subject") or "",
    }


def _request(method, path, payload=None, idempotency_key=None):
    _require_access()
    if not path.startswith("/api/erpnext/") or ".." in path:
        frappe.throw(_("Invalid Starcloud API path."), StarcloudProxyError)

    base_url, timeout, shared_secret = _settings()
    request_id = _request_id()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
        "X-Starcloud-Proxy-Secret": shared_secret,
        "X-Starcloud-Context": json.dumps(_context(request_id), separators=(",", ":")),
    }
    if idempotency_key is not None:
        idempotency_key = str(idempotency_key).strip()
        if not idempotency_key or len(idempotency_key) > 128:
            frappe.throw(_("Invalid idempotency key."), StarcloudProxyError)
        headers["X-Idempotency-Key"] = idempotency_key

    started_at = time.monotonic()
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    upstream_request = Request(f"{base_url}{path}", data=body, headers=headers, method=method)
    status_code = 0
    try:
        with urlopen(upstream_request, timeout=timeout) as response:
            status_code = response.status
            response_body = response.read().decode("utf-8")
            return {"data": json.loads(response_body) if response_body else None, "request_id": request_id}
    except HTTPError as error:
        status_code = error.code
        frappe.throw(_("Starcloud returned HTTP status {0}.").format(error.code), StarcloudProxyError)
    except (URLError, TimeoutError):
        frappe.throw(_("Starcloud is temporarily unavailable."), StarcloudProxyError)
    finally:
        logger = frappe.logger("starcloud_integration", allow_site=True)
        logger.setLevel(logging.INFO)
        logger.info(
            "starcloud_proxy method=%s path=%s status=%s duration_ms=%s user=%s request_id=%s",
            method,
            path,
            status_code,
            int((time.monotonic() - started_at) * 1000),
            frappe.session.user,
            request_id,
        )


@frappe.whitelist()
def current_user():
    _require_access()
    request_id = _request_id()
    return {"data": _context(request_id), "request_id": request_id}


@frappe.whitelist()
def health_check():
    _require_access()
    path = frappe.conf.get("starcloud_health_path") or "/api/erpnext/health"
    return _request("GET", path)


@frappe.whitelist()
def dashboard_stats():
    _require_access()
    return _request("GET", "/api/erpnext/dashboard-stats")


@frappe.whitelist()
def applications(page=1, page_size=20, status=None, name=None, owner=None):
    _require_access()
    page = _positive_int(page, _("page"))
    page_size = _positive_int(page_size, _("page size"))
    if page_size > 100:
        frappe.throw(_("Page size cannot exceed 100."), StarcloudProxyError)

    params = {"page": page, "page_size": page_size}
    if status not in (None, ""):
        try:
            status = int(status)
        except (TypeError, ValueError):
            frappe.throw(_("Application status must be an integer."), StarcloudProxyError)
        if status not in (10, 20, 30, 40):
            frappe.throw(_("Invalid application status."), StarcloudProxyError)
        params["status"] = status
    for key, value in (("name", name), ("owner", owner)):
        if value:
            value = str(value).strip()
            if len(value) > 255:
                frappe.throw(_("Search text cannot exceed 255 characters."), StarcloudProxyError)
            params[key] = value
    return _request("GET", "/api/erpnext/applications?" + urlencode(params))


@frappe.whitelist()
def application(application_id):
    _require_access()
    application_id = _positive_int(application_id, _("application ID"))
    return _request("GET", f"/api/erpnext/applications/{application_id}")


@frappe.whitelist()
def approve_application(application_id, idempotency_key):
    _require_review()
    application_id = _positive_int(application_id, _("application ID"))
    return _request("POST", f"/api/erpnext/applications/{application_id}/approve", {}, idempotency_key)


@frappe.whitelist()
def reject_application(application_id, idempotency_key):
    _require_review()
    application_id = _positive_int(application_id, _("application ID"))
    return _request("POST", f"/api/erpnext/applications/{application_id}/reject", {}, idempotency_key)