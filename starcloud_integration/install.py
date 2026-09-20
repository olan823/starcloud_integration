import json

import frappe


ROLES = ["Starcloud User", "Starcloud Admin"]
WORKSPACE_NAME = "Starcloud"
SHORTCUTS = [("应用审核", "starcloud-applications")]
APP_NAME = "starcloud_integration"
APP_LOGO_URL = "/assets/starcloud_integration/images/starcloud.svg?v=0.1.6"
APP_HOME = "/app/starcloud"


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

    content = json.dumps(
        [
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
            "roles": [{"role": role} for role in [*ROLES, "System Manager"]],
        }
    )

    if workspace.is_new():
        workspace.insert(ignore_permissions=True)
    else:
        workspace.save(ignore_permissions=True)

    frappe.clear_cache()


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