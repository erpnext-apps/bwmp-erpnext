import frappe


def on_submit_event(doc, method=None):
	set_batch_details(doc)

def set_batch_details(doc):
	fields = ["length", "width", "thickness", "weight", "custom_grade", "custom_tracking_no"]

	for row in doc.items:
		if not row.s_warehouse and row.t_warehouse and row.serial_and_batch_bundle:
			update_value = {}
			for field in fields:
				if row.get(field):
					update_value[field] = row.get(field)

			s_doc = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
			for d in s_doc.entries:
				if d.batch_no:
					frappe.db.set_value("Serial and Batch Entry", d.name, update_value)
					frappe.db.set_value("Batch", d.batch_no, update_value)