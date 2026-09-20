import json

import frappe


ROLES = ["Starcloud User", "Starcloud Admin"]
WORKSPACE_NAME = "Starcloud"
SHORTCUTS = [("应用审核", "starcloud-applications")]
APP_NAME = "starcloud_integration"
APP_LOGO_URL = "/assets/starcloud_integration/images/starcloud.svg?v=0.1.6"
APP_HOME = "/app/starcloud"
DASHBOARD_BLOCK_NAME = "Starcloud Dashboard Statistics"
DASHBOARD_HTML = """
<section class="dashboard" aria-labelledby="dashboard-title">
    <div class="dashboard__heading">
        <div>
            <p class="dashboard__eyebrow">实时数据</p>
            <h2 id="dashboard-title">星云应用审核</h2>
        </div>
        <button class="dashboard__refresh" type="button">刷新</button>
    </div>
    <div class="dashboard__metrics" aria-live="polite">
        <a class="metric metric--pending" href="/app/starcloud-applications">
            <span class="metric__label">审核中</span>
            <strong class="metric__value" data-stat="pending_review">--</strong>
            <span class="metric__hint">等待审核</span>
        </a>
        <a class="metric metric--approved" href="/app/starcloud-applications">
            <span class="metric__label">已审核</span>
            <strong class="metric__value" data-stat="approved">--</strong>
            <span class="metric__hint">审核通过</span>
        </a>
        <a class="metric metric--rejected" href="/app/starcloud-applications">
            <span class="metric__label">审核驳回</span>
            <strong class="metric__value" data-stat="rejected">--</strong>
            <span class="metric__hint">未通过审核</span>
        </a>
    </div>
    <div class="dashboard__error" role="alert" hidden>
        <span>统计数据暂时无法加载。</span>
        <button type="button" data-action="retry">重试</button>
    </div>
</section>
"""
DASHBOARD_STYLE = """
:host { display: block; }
.dashboard { color: var(--text-color); padding: 4px 0 12px; }
.dashboard__heading { align-items: end; display: flex; justify-content: space-between; margin-bottom: 16px; }
.dashboard__eyebrow { color: var(--text-muted); font-size: 12px; font-weight: 600; margin: 0 0 4px; }
.dashboard h2 { font-size: 20px; font-weight: 650; line-height: 1.3; margin: 0; }
.dashboard__refresh, .dashboard__error button { background: var(--control-bg); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-color); cursor: pointer; min-height: 32px; padding: 5px 12px; }
.dashboard__refresh:disabled { cursor: wait; opacity: .6; }
.dashboard__metrics { display: grid; gap: 12px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.metric { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; color: inherit; display: flex; flex-direction: column; min-height: 132px; padding: 18px; position: relative; text-decoration: none; }
.metric::before { background: var(--accent); content: ""; height: 3px; left: 18px; position: absolute; right: 18px; top: 0; }
.metric:hover { border-color: var(--accent); color: inherit; text-decoration: none; }
.metric--pending { --accent: #d97706; }
.metric--approved { --accent: #16a34a; }
.metric--rejected { --accent: #dc2626; }
.metric__label { color: var(--text-muted); font-size: 13px; }
.metric__value { font-size: 30px; font-weight: 700; line-height: 1.2; margin-top: 14px; overflow-wrap: anywhere; }
.metric__hint { color: var(--text-muted); font-size: 12px; margin-top: auto; padding-top: 10px; }
.dashboard__error { align-items: center; background: var(--subtle-fg); border: 1px solid var(--border-color); border-radius: 8px; display: flex; gap: 12px; justify-content: space-between; margin-top: 12px; padding: 12px 14px; }
.dashboard__error[hidden] { display: none; }
@media (max-width: 760px) { .dashboard__metrics { grid-template-columns: 1fr; } .metric { min-height: 118px; } }
"""
DASHBOARD_SCRIPT = """
const refresh_button = root_element.querySelector(".dashboard__refresh");
const retry_button = root_element.querySelector('[data-action="retry"]');
const error_box = root_element.querySelector(".dashboard__error");
const formatter = new Intl.NumberFormat();

const set_value = (name, value) => {
    root_element.querySelector(`[data-stat="${name}"]`).textContent = formatter.format(value);
};

const load_stats = async () => {
    refresh_button.disabled = true;
    error_box.hidden = true;
    try {
        const response = await frappe.call({
            method: "starcloud_integration.api.proxy.dashboard_stats",
        });
        const stats = response.message.data.data;
        set_value("pending_review", stats.pending_review);
        set_value("approved", stats.approved);
        set_value("rejected", stats.rejected);
    } catch (error) {
        error_box.hidden = false;
    } finally {
        refresh_button.disabled = false;
    }
};

refresh_button.addEventListener("click", load_stats);
retry_button.addEventListener("click", load_stats);
load_stats();
"""


def after_install():
    ensure_roles()
    ensure_module_def()
    ensure_workspace()


def after_uninstall():
    if frappe.db.exists("Workspace", WORKSPACE_NAME):
        frappe.delete_doc("Workspace", WORKSPACE_NAME, force=True, ignore_permissions=True)


def ensure_roles():
    for role_name in ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)


def ensure_module_def():
    if not frappe.db.exists("Module Def", WORKSPACE_NAME):
        frappe.get_doc(
            {"doctype": "Module Def", "module_name": WORKSPACE_NAME, "app_name": "starcloud_integration"}
        ).insert(ignore_permissions=True)


def ensure_workspace():
    ensure_roles()
    ensure_module_def()
    ensure_desktop_icon()
    ensure_dashboard_block()

    content = json.dumps(
        [{
            "id": "starcloud-dashboard-statistics",
            "type": "custom_block",
            "data": {"custom_block_name": DASHBOARD_BLOCK_NAME, "col": 12},
        }] + [
            {
                "id": f"starcloud-shortcut-{index}",
                "type": "shortcut",
                "data": {"shortcut_name": label},
            }
            for index, (label, page_name) in enumerate(SHORTCUTS, start=1)
        ]
    )
    workspace = (
        frappe.get_doc("Workspace", WORKSPACE_NAME)
        if frappe.db.exists("Workspace", WORKSPACE_NAME)
        else frappe.new_doc("Workspace")
    )
    workspace.update(
        {
            "label": WORKSPACE_NAME,
            "title": WORKSPACE_NAME,
            "module": WORKSPACE_NAME,
            "icon": "cloud",
            "public": 1,
            "is_hidden": 0,
            "content": content,
            "shortcuts": [
                {"label": label, "type": "Page", "link_to": page_name}
                for label, page_name in SHORTCUTS
            ],
            "custom_blocks": [
                {"label": DASHBOARD_BLOCK_NAME, "custom_block_name": DASHBOARD_BLOCK_NAME}
            ],
            "roles": [{"role": role} for role in [*ROLES, "System Manager"]],
        }
    )

    if workspace.is_new():
        workspace.insert(ignore_permissions=True)
    else:
        workspace.save(ignore_permissions=True)

    ensure_custom_workspace_dashboard_block()
    frappe.clear_cache()


def ensure_custom_workspace_dashboard_block():
    customization_name = frappe.db.exists("Custom Workspace", {"workspace": WORKSPACE_NAME})
    if not customization_name:
        return

    customization = frappe.get_doc("Custom Workspace", customization_name)
    if not customization.content:
        return

    content = frappe.parse_json(customization.content)
    if any(
        block.get("type") == "custom_block"
        and block.get("data", {}).get("custom_block_name") == DASHBOARD_BLOCK_NAME
        for block in content
    ):
        return

    content.insert(
        0,
        {
            "id": "starcloud-dashboard-statistics",
            "type": "custom_block",
            "data": {"custom_block_name": DASHBOARD_BLOCK_NAME, "col": 12},
        },
    )
    customization.content = json.dumps(content)
    customization.save(ignore_permissions=True)


def ensure_dashboard_block():
    if frappe.db.exists("Custom HTML Block", DASHBOARD_BLOCK_NAME):
        block = frappe.get_doc("Custom HTML Block", DASHBOARD_BLOCK_NAME)
    else:
        block = frappe.new_doc("Custom HTML Block")
        block.name = DASHBOARD_BLOCK_NAME
    block.update(
        {
            "private": 0,
            "html": DASHBOARD_HTML,
            "style": DASHBOARD_STYLE,
            "script": DASHBOARD_SCRIPT,
            "roles": [{"role": role} for role in [*ROLES, "System Manager"]],
        }
    )
    if block.is_new():
        block.insert(ignore_permissions=True)
    else:
        block.save(ignore_permissions=True)


def ensure_desktop_icon():
    app_icon_names = frappe.get_all(
        "Desktop Icon",
        filters={"app": APP_NAME, "icon_type": "App"},
        pluck="name",
        order_by="creation asc",
    )
    matching_icon_names = frappe.get_all(
        "Desktop Icon", filters={"label": WORKSPACE_NAME}, pluck="name", order_by="creation asc"
    )
    icon_name = app_icon_names[0] if app_icon_names else None
    icon_name = icon_name or (matching_icon_names[0] if matching_icon_names else None)

    for duplicate_name in dict.fromkeys([*app_icon_names, *matching_icon_names]):
        if duplicate_name != icon_name:
            frappe.delete_doc("Desktop Icon", duplicate_name, force=True, ignore_permissions=True)

    icon = (
        frappe.get_doc("Desktop Icon", icon_name) if icon_name else frappe.new_doc("Desktop Icon")
    )
    icon.update(
        {
            "label": WORKSPACE_NAME,
            "link_type": "External",
            "link_to": None,
            "icon_type": "App",
            "app": APP_NAME,
            "link": APP_HOME,
            "logo_url": APP_LOGO_URL,
        }
    )

    if icon.is_new():
        icon.insert(ignore_permissions=True)
    else:
        icon.save(ignore_permissions=True)

    frappe.cache.delete_key("desktop_icons")
    frappe.cache.delete_key("bootinfo")