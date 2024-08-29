import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def execute():
	create_custom_field(
		"Serial and Batch Entry",
		dict(fieldname="section_break_batch_dimension", label="Batch Dimension", fieldtype="Section Break", insert_after="stock_queue")
	)

	for field in ["length", "weight", "thickness", "width"]:
		create_custom_field(
			"Serial and Batch Entry",
			dict(fieldname=field, label=field.title(), fieldtype="Float", in_list_view=1, insert_after="section_break_batch_dimension")
		)

	create_custom_field(
		"Serial and Batch Entry",
		dict(fieldname="col_break_batch_dimension", label=" ", fieldtype="Column Break", insert_after="length")
	)

	for field in ["custom_grade", "custom_tracking_no"]:
		label = field.replace("custom_", "").title()
		create_custom_field(
			"Serial and Batch Entry",
			dict(fieldname=field, label=label, fieldtype="Data", insert_after="col_break_batch_dimension")
		)