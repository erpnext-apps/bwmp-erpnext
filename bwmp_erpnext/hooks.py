from . import __version__ as app_version

app_name = "bwmp_erpnext"
app_title = "BWMP ERPNext"
app_publisher = "Frappe"
app_description = "Banaraswala Wire Mesh Private Limited"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "test@test.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/bwmp_erpnext/css/bwmp_erpnext.css"
# app_include_js = "/assets/bwmp_erpnext/js/bwmp_erpnext.js"

# include js, css files in header of web template
# web_include_css = "/assets/bwmp_erpnext/css/bwmp_erpnext.css"
app_include_js = "/assets/bwmp_erpnext/js/serial_no_batch_selector.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "bwmp_erpnext/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

fixtures = [
	{
		"dt": "Server Script"
	}
]

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Payment Order" : "bwmp_erpnext/setup.js",
	"Stock Entry" : "bwmp_erpnext/stock_entry.js"
}

# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "bwmp_erpnext.utils.jinja_methods",
# 	"filters": "bwmp_erpnext.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "bwmp_erpnext.install.before_install"
# after_install = "bwmp_erpnext.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "bwmp_erpnext.uninstall.before_uninstall"
# after_uninstall = "bwmp_erpnext.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "bwmp_erpnext.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Payment Order": {
		"validate": "bwmp_erpnext.bwmp_erpnext.setup.validate_payment_order",
		"on_cancel": "bwmp_erpnext.bwmp_erpnext.setup.unlink_uat_no_and_uat_date"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"bwmp_erpnext.tasks.all"
# 	],
# 	"daily": [
# 		"bwmp_erpnext.tasks.daily"
# 	],
# 	"hourly": [
# 		"bwmp_erpnext.tasks.hourly"
# 	],
# 	"weekly": [
# 		"bwmp_erpnext.tasks.weekly"
# 	],
# 	"monthly": [
# 		"bwmp_erpnext.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "bwmp_erpnext.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "bwmp_erpnext.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "bwmp_erpnext.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"bwmp_erpnext.auth.validate"
# ]

