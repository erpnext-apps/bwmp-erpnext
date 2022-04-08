# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_columns(filters):
	return [
		{
			"fieldname": "nature_of_document",
			"label": _("Nature of Document"),
			"fieldtype": "Data",
			"width": 300
		},
		{
			"fieldname": "naming_series",
			"label": _("Series"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "from_serial_no",
			"label": _("Serial Number From"),
			"fieldtype": "Data",
			"width": 160
		},
		{
			"fieldname": "to_serial_no",
			"label": _("Serial Number To"),
			"fieldtype": "Data",
			"width": 160
		},
		{
			"fieldname": "total_number",
			"label": _("Total Submitted Number"),
			"fieldtype": "Int",
			"width": 180
		},
		{
			"fieldname": "canceled",
			"label": _("Canceled Number"),
			"fieldtype": "Int",
			"width": 160
		}
	]

def get_data(filters) -> list:
	data = []
	bank_accounts = frappe.db.sql_list(""" SELECT
		name from `tabAccount` where account_type = 'Bank' """)

	document_mapper = {
		"Invoices for outward supply": {
			"doctype": "Sales Invoice"
		},
		"Invoices for inward supply": {
			"doctype": "Purchase Invoice",
			"condition": "gst_category != 'Unregistered'"
		},
		"Invoices for inward supply from unregistered person": {
			"doctype": "Purchase Invoice",
			"condition": "gst_category = 'Unregistered'"
		},
		"Debit Note": {
			"doctype": "Purchase Invoice",
			"condition": "is_return = 1"
		},
		"Credit Note": {
			"doctype": "Sales Invoice",
			"condition": "is_return = 1"
		},
		"Receipt Voucher": {
			"doctype": "Payment Entry",
			"condition": "payment_type =  'Receive'"
		},
		"Payment Voucher": {
			"doctype": "Payment Entry",
			"condition": "payment_type =  'Pay'"
		},
		"Receipt Voucher (JV)": {
			"doctype": "Journal Entry",
			"condition": (f"""name in (
				SELECT distinct parent from `tabJournal Entry Account`
					where account in {tuple(bank_accounts)} and debit > 0 and credit = 0)
				and voucher_type not in ('Contra Entry')
			""")
		},
		"Payment Voucher (JV)": {
			"doctype": "Journal Entry",
			"condition": (f"""name in (
				SELECT distinct parent from `tabJournal Entry Account`
					where account in {tuple(bank_accounts)} and debit = 0 and credit > 0)
				and voucher_type not in ('Contra Entry')
			""")
		}
	}

	for nature_of_document, document_details in document_mapper.items():
		document_details = frappe._dict(document_details)
		data.extend(get_document_summary(filters, document_details, nature_of_document))

	return data

def get_document_summary(filters, document_details, nature_of_document):
	condition = (f"""company = {frappe.db.escape(filters.company)}
		AND creation BETWEEN '{filters.from_date} 00:00:00' AND '{filters.to_date} 23:59:59'
		AND document_naming_series IS NOT NULL """)

	if document_details.condition:
		condition += f" AND {document_details.condition}"

	for field in ["company_gstin", "company_address"]:
		if filters.get(field):
			if document_details.doctype == "Purchase Invoice":
				condition += f" AND shipping_address = '{filters.get(field)}'"
			else:
				condition += f" AND {field} = '{filters.get(field)}'"

	data = frappe.db.sql(f"""
		SELECT
			MIN(name) as from_serial_no, MAX(name) as to_serial_no,
			COUNT(name) as total_number, document_naming_series as naming_series
		FROM
			`tab{document_details.doctype}`
		WHERE
			{condition}
		GROUP BY
			document_naming_series
	""", as_dict=1, debug=1)

	canceled_documents = frappe.db.sql(f"""
		SELECT
			COUNT(name) as total_number, document_naming_series as naming_series
		FROM
			`tab{document_details.doctype}`
		WHERE
			{condition} AND docstatus = 2
		GROUP BY
			document_naming_series
	""", as_dict=1) or {}

	if canceled_documents:
		canceled_documents = {row.naming_series: row.total_number for row in canceled_documents}

	for item in data:
		item.nature_of_document = nature_of_document
		item.canceled = canceled_documents.get(item.naming_series)

	return data