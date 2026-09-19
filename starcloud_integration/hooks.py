app_name = "starcloud_integration"
app_title = "Starcloud Integration"
app_publisher = "Skychip"
app_description = "Native ERPNext integration boundary for Starcloud"
app_email = ""
app_license = "MIT"
app_logo_url = "/assets/starcloud_integration/images/starcloud.svg?v=0.1.6"
app_home = "/app/starcloud"

add_to_apps_screen = [
	{
		"name": app_name,
		"logo": app_logo_url,
		"title": "Starcloud",
		"route": app_home,
	}
]

after_install = "starcloud_integration.install.after_install"
after_migrate = "starcloud_integration.install.ensure_workspace"
after_uninstall = "starcloud_integration.install.after_uninstall"