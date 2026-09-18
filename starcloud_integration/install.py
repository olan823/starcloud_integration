import json

import frappe


ROLES = ["Starcloud User", "Starcloud Admin"]
WORKSPACE_NAME = "Starcloud"
SHORTCUTS = [("应用审核", "starcloud-applications")]


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

    frappe.clear_cache(doctype="Workspace")