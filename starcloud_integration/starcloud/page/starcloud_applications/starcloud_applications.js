frappe.pages["starcloud-applications"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Starcloud"), single_column: true });
	const content = $('<div class="starcloud-applications"></div>').appendTo(page.main);
	let currentPage = 1;
	let canReview = false;

	function call(method, args = {}) {
		return frappe.call({ method: `starcloud_integration.api.proxy.${method}`, args });
	}

	function upstream(response) {
		return response.message.data.data;
	}

	function randomKey() {
		return window.crypto && window.crypto.randomUUID
			? window.crypto.randomUUID()
			: `${Date.now()}-${Math.random().toString(36).slice(2)}`;
	}

	function formatDate(value) {
		return value ? frappe.datetime.str_to_user(value) : "";
	}

	function review(application, action, dialog) {
		const approved = action === "approve_application";
		frappe.confirm(
			approved ? __("Approve application {0}?", [application.title]) : __("Reject application {0}?", [application.title]),
			() => call(action, { application_id: application.id, idempotency_key: randomKey() })
				.then(() => {
					dialog.hide();
					frappe.show_alert({ message: approved ? __("Application approved.") : __("Application rejected."), indicator: "green" });
					loadApplications(currentPage);
				})
				.catch(() => frappe.msgprint(__("Unable to review this application.")))
		);
	}

	function showApplication(applicationId) {
		call("application", { application_id: applicationId }).then((response) => {
			const application = upstream(response);
			const escape = frappe.utils.escape_html;
			const owner = application.owner || {};
			const dialog = new frappe.ui.Dialog({
				title: escape(application.title),
				fields: [{
					fieldtype: "HTML",
					options: '<table class="table table-bordered"><tbody>' +
						`<tr><th>${__("Developer")}</th><td>${escape(owner.name || "")} &lt;${escape(owner.email || "")}&gt;</td></tr>` +
						`<tr><th>${__("Status")}</th><td>${escape(application.status_title || "")}</td></tr>` +
						`<tr><th>${__("Description")}</th><td>${escape(application.description || "")}</td></tr>` +
						`<tr><th>${__("Application types")}</th><td>${escape((application.type || []).join(", "))}</td></tr>` +
						`<tr><th>${__("Callback URL")}</th><td>${escape(application.callback_url || "")}</td></tr>` +
						`<tr><th>${__("Callback events")}</th><td>${escape((application.callback_events || []).join(", "))}</td></tr>` +
						`<tr><th>${__("Created")}</th><td>${escape(formatDate(application.created_at))}</td></tr>` +
						"</tbody></table>",
				}],
			});
			if (canReview && application.status === 20) {
				dialog.set_primary_action(__("Approve"), () => review(application, "approve_application", dialog));
				dialog.set_secondary_action_label(__("Reject"));
				dialog.set_secondary_action(() => review(application, "reject_application", dialog));
			}
			dialog.show();
		}).catch(() => frappe.msgprint(__("Unable to load application details.")));
	}

	function loadApplications(pageNumber) {
		const args = {
			page: pageNumber,
			page_size: 20,
			status: content.find(".starcloud-status").val() || null,
			name: content.find(".starcloud-name").val() || "",
			owner: content.find(".starcloud-owner").val() || "",
		};
		content.find(".starcloud-results").html(`<div class="text-muted">${__("Loading...")}</div>`);
		call("applications", args).then((response) => {
			const payload = upstream(response);
			const escape = frappe.utils.escape_html;
			currentPage = payload.pagination.page;
			const rows = payload.items.map((application) => {
				const owner = application.owner || {};
				return `<tr><td>${application.id}</td><td>${escape(application.title || "")}</td>` +
					`<td>${escape(owner.name || owner.email || "")}</td><td>${escape(application.callback_url || "")}</td>` +
					`<td>${escape(application.status_title || "")}</td><td>${escape(formatDate(application.created_at))}</td>` +
					`<td><button class="btn btn-default btn-xs application-view" data-id="${application.id}">${__("Details")}</button></td></tr>`;
			}).join("") || `<tr><td colspan="7" class="text-muted text-center">${__("No applications found.")}</td></tr>`;
			content.find(".starcloud-results").html(
				'<table class="table table-bordered"><thead><tr>' +
				`<th>ID</th><th>${__("Application")}</th><th>${__("Developer")}</th><th>${__("Callback URL")}</th>` +
				`<th>${__("Status")}</th><th>${__("Created")}</th><th>${__("Actions")}</th></tr></thead><tbody>${rows}</tbody></table>` +
				'<div class="flex justify-between align-center">' +
				`<span class="text-muted">${__("{0} records", [payload.pagination.total])}</span>` +
				`<div><button class="btn btn-default btn-sm application-previous" ${currentPage <= 1 ? "disabled" : ""}>${__("Previous")}</button> ` +
				`<button class="btn btn-default btn-sm application-next" ${currentPage >= payload.pagination.last_page ? "disabled" : ""}>${__("Next")}</button></div></div>`
			);
		}).catch(() => content.find(".starcloud-results").html(`<div class="text-danger">${__("Unable to load applications.")}</div>`));
	}

	call("current_user").then((response) => {
		const roles = response.message.data.roles || [];
		canReview = roles.includes("Starcloud Admin") || roles.includes("System Manager");
		content.html(
			'<div class="form-layout"><div class="form-page"><div class="form-dashboard-section">' +
			`<div class="section-head">${__("Application review")}</div>` +
			'<div class="row mb-3"><div class="col-sm-3"><input class="form-control starcloud-name" placeholder="' + __("Application name") + '"></div>' +
			'<div class="col-sm-3"><input class="form-control starcloud-owner" placeholder="' + __("Developer name or email") + '"></div>' +
			'<div class="col-sm-3"><select class="form-control starcloud-status"><option value="">' + __("All statuses") + '</option>' +
			'<option value="20">' + __("Pending review") + '</option><option value="30">' + __("Approved") + '</option>' +
			'<option value="40">' + __("Rejected") + '</option><option value="10">' + __("Created") + '</option></select></div>' +
			'<div class="col-sm-3"><button class="btn btn-primary application-search">' + __("Search") + '</button></div></div>' +
			'<div class="starcloud-results"></div></div></div></div>'
		);
		content.on("click", ".application-search", () => loadApplications(1));
		content.on("click", ".application-view", (event) => showApplication($(event.currentTarget).data("id")));
		content.on("click", ".application-previous", () => loadApplications(currentPage - 1));
		content.on("click", ".application-next", () => loadApplications(currentPage + 1));
		content.on("keydown", ".starcloud-name, .starcloud-owner", (event) => { if (event.key === "Enter") loadApplications(1); });
		loadApplications(1);
	}).catch(() => content.html(`<div class="text-danger">${__("Unable to load Starcloud identity.")}</div>`));
};