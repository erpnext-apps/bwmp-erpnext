import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field, create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def execute():
	df = dict(fieldname="document_naming_series", hidden=1,
		label='Document Naming Series', fieldtype='Data')

	frappe.reload_doc("accounts", "doctype", "tax_withheld_vouchers")
	for doctype in ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry"]:
		frappe.reload_doc("accounts", "doctype", frappe.scrub(doctype))
		create_custom_field(doctype, df)

		frappe.db.sql(f"""
			UPDATE
				`tab{doctype}`
			SET
				document_naming_series = naming_series
			WHERE
				naming_series IS NOT NULL
		""")
