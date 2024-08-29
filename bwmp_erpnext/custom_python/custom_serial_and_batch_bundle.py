import frappe, csv
from frappe import _, _dict, bold
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import get_auto_data
from frappe.utils import (
	cint,
	cstr,
	flt,
	now,
	parse_json,
)

@frappe.whitelist()
def get_data(**kwargs):
	data = get_auto_data(**kwargs)

	for row in data:
		batch_details = frappe.db.get_value("Batch", row.get("batch_no"), ["length", "weight", "thickness", "width", "custom_grade", "custom_tracking_no"], as_dict=1)
		row.update(batch_details)

	return data

@frappe.whitelist()
def upload_csv_file(item_code, file_path):
	serial_nos, batch_nos = [], []
	serial_nos, batch_nos = get_serial_batch_from_csv(item_code, file_path)

	return {
		"serial_nos": serial_nos,
		"batch_nos": batch_nos,
	}


def get_serial_batch_from_csv(item_code, file_path):
	if "private" in file_path:
		file_path = frappe.get_site_path() + file_path
	else:
		file_path = frappe.get_site_path() + "/public" + file_path

	serial_nos = []
	batch_nos = []

	with open(file_path) as f:
		reader = csv.reader(f)
		serial_nos, batch_nos = parse_csv_file_to_get_serial_batch(reader)

	if serial_nos:
		make_serial_nos(item_code, serial_nos)

	if batch_nos:
		make_batch_nos(item_code, batch_nos)

	return serial_nos, batch_nos


def parse_csv_file_to_get_serial_batch(reader):
	has_serial_no, has_batch_no = False, False
	serial_nos = []
	batch_nos = []

	for index, row in enumerate(reader):
		if index == 0:
			has_serial_no = row[0] == "Serial No"
			has_batch_no = row[0] == "Batch No"
			if not has_batch_no and len(row) > 1:
				has_batch_no = row[1] == "Batch No"

			continue

		if not row[0]:
			continue

		if has_serial_no or (has_serial_no and has_batch_no):
			_dict = {"serial_no": row[0], "qty": 1}

			if has_batch_no:
				_dict.update(
					{
						"batch_no": row[1],
						"qty": row[2],
					}
				)

				batch_nos.append(
					{
						"batch_no": row[1],
						"qty": row[2],
					}
				)

			serial_nos.append(_dict)
		elif has_batch_no:
			batch_nos.append(
				{
					"batch_no": row[0],
					"qty": row[1],
					"length": row[2],
					"width": row[3],
					"weight": row[4],
					"thickness": row[5],
					"custom_grade": row[6],
					"custom_tracking_no": row[7],
				}
			)

	return serial_nos, batch_nos

def make_serial_nos(item_code, serial_nos):
	item = frappe.get_cached_value(
		"Item", item_code, ["description", "item_code", "item_name", "warranty_period"], as_dict=1
	)

	serial_nos = [d.get("serial_no") for d in serial_nos if d.get("serial_no")]
	existing_serial_nos = frappe.get_all("Serial No", filters={"name": ("in", serial_nos)})

	existing_serial_nos = [d.get("name") for d in existing_serial_nos if d.get("name")]
	serial_nos = list(set(serial_nos) - set(existing_serial_nos))

	if not serial_nos:
		return

	serial_nos_details = []
	user = frappe.session.user
	for serial_no in serial_nos:
		serial_nos_details.append(
			(
				serial_no,
				serial_no,
				now(),
				now(),
				user,
				user,
				item.item_code,
				item.item_name,
				item.description,
				item.warranty_period or 0,
				"Inactive",
			)
		)

	fields = [
		"name",
		"serial_no",
		"creation",
		"modified",
		"owner",
		"modified_by",
		"item_code",
		"item_name",
		"description",
		"warranty_period",
		"status",
	]

	frappe.db.bulk_insert("Serial No", fields=fields, values=set(serial_nos_details))

	frappe.msgprint(_("Serial Nos are created successfully"), alert=True)


def make_batch_nos(item_code, batch_nos):
	item = frappe.get_cached_value("Item", item_code, ["description", "item_code"], as_dict=1)
	batch_nos = [d.get("batch_no") for d in batch_nos if d.get("batch_no")]

	existing_batches = frappe.get_all("Batch", filters={"name": ("in", batch_nos)})

	existing_batches = [d.get("name") for d in existing_batches if d.get("name")]

	batch_nos = list(set(batch_nos) - set(existing_batches))
	if not batch_nos:
		return

	batch_nos_details = []
	user = frappe.session.user
	for batch_no in batch_nos:
		if frappe.db.exists("Batch", batch_no):
			continue

		batch_nos_details.append(
			(
				batch_no,
				batch_no,
				now(),
				now(),
				user,
				user,
				item.item_code,
				item.item_name,
				item.description,
				1,
			)
		)

	fields = [
		"name",
		"batch_id",
		"creation",
		"modified",
		"owner",
		"modified_by",
		"item",
		"item_name",
		"description",
		"use_batchwise_valuation",
	]

	frappe.db.bulk_insert("Batch", fields=fields, values=set(batch_nos_details))

	frappe.msgprint(_("Batch Nos are created successfully"), alert=True)


def parse_serial_nos(data):
	if isinstance(data, list):
		return data

	return [s.strip() for s in cstr(data).strip().replace(",", "\n").split("\n") if s.strip()]


@frappe.whitelist()
def add_serial_batch_ledgers(entries, child_row, doc, warehouse, do_not_save=False) -> object:
	if isinstance(child_row, str):
		child_row = frappe._dict(parse_json(child_row))

	if isinstance(entries, str):
		entries = parse_json(entries)

	parent_doc = doc
	if parent_doc and isinstance(parent_doc, str):
		parent_doc = parse_json(parent_doc)

	if frappe.db.exists("Serial and Batch Bundle", child_row.serial_and_batch_bundle):
		sb_doc = update_serial_batch_no_ledgers(entries, child_row, parent_doc, warehouse)
	else:
		sb_doc = create_serial_batch_no_ledgers(
			entries, child_row, parent_doc, warehouse, do_not_save=do_not_save
		)

	return sb_doc


def create_serial_batch_no_ledgers(
	entries, child_row, parent_doc, warehouse=None, do_not_save=False
) -> object:
	warehouse = warehouse or (child_row.rejected_warehouse if child_row.is_rejected else child_row.warehouse)

	type_of_transaction = get_type_of_transaction(parent_doc, child_row)
	if parent_doc.get("doctype") == "Stock Entry":
		warehouse = warehouse or child_row.s_warehouse or child_row.t_warehouse

	doc = frappe.get_doc(
		{
			"doctype": "Serial and Batch Bundle",
			"voucher_type": child_row.parenttype,
			"item_code": child_row.item_code,
			"warehouse": warehouse,
			"is_rejected": child_row.is_rejected,
			"type_of_transaction": type_of_transaction,
			"posting_date": parent_doc.get("posting_date"),
			"posting_time": parent_doc.get("posting_time"),
			"company": parent_doc.get("company"),
		}
	)

	for row in entries:
		row = frappe._dict(row)
		doc.append(
			"entries",
			{
				"qty": (flt(row.qty) or 1.0) * (1 if type_of_transaction == "Inward" else -1),
				"warehouse": warehouse,
				"batch_no": row.batch_no,
				"serial_no": row.serial_no,
				"length": row.length,
				"width": row.width,
				"weight": row.weight,
				"thickness": row.thickness,
				"custom_grade": row.custom_grade,
				"custom_tracking_no": row.custom_tracking_no,
			},
		)

	doc.save()

	if do_not_save:
		frappe.db.set_value(child_row.doctype, child_row.name, "serial_and_batch_bundle", doc.name)

	frappe.msgprint(_("Serial and Batch Bundle created"), alert=True)

	return doc

def update_serial_batch_no_ledgers(entries, child_row, parent_doc, warehouse=None) -> object:
	doc = frappe.get_doc("Serial and Batch Bundle", child_row.serial_and_batch_bundle)
	doc.voucher_detail_no = child_row.name
	doc.posting_date = parent_doc.posting_date
	doc.posting_time = parent_doc.posting_time
	doc.warehouse = warehouse or doc.warehouse
	doc.set("entries", [])

	for d in entries:
		doc.append(
			"entries",
			{
				"qty": (flt(d.get("qty")) or 1.0) * (1 if doc.type_of_transaction == "Inward" else -1),
				"warehouse": warehouse or d.get("warehouse"),
				"batch_no": d.get("batch_no"),
				"serial_no": d.get("serial_no"),
				"length": d.get("length"),
				"width": d.get("width"),
				"weight": d.get("weight"),
				"thickness": d.get("thickness"),
				"custom_grade": d.get("custom_grade"),
				"custom_tracking_no": d.get("custom_tracking_no"),
			},
		)

	doc.save(ignore_permissions=True)

	frappe.msgprint(_("Serial and Batch Bundle updated"), alert=True)

	return doc

@frappe.whitelist()
def get_serial_batch_ledgers(item_code=None, docstatus=None, voucher_no=None, name=None, child_row=None):
	filters = get_filters_for_bundle(
		item_code=item_code, docstatus=docstatus, voucher_no=voucher_no, name=name, child_row=child_row
	)

	fields = [
		"`tabSerial and Batch Bundle`.`item_code`",
		"`tabSerial and Batch Entry`.`qty`",
		"`tabSerial and Batch Entry`.`warehouse`",
		"`tabSerial and Batch Entry`.`batch_no`",
		"`tabSerial and Batch Entry`.`serial_no`",
		"`tabSerial and Batch Entry`.`length`",
		"`tabSerial and Batch Entry`.`width`",
		"`tabSerial and Batch Entry`.`weight`",
		"`tabSerial and Batch Entry`.`thickness`",
		"`tabSerial and Batch Entry`.`custom_grade`",
		"`tabSerial and Batch Entry`.`custom_tracking_no`",
		"`tabSerial and Batch Entry`.`name` as `child_row`",
	]

	if not child_row:
		fields.append("`tabSerial and Batch Bundle`.`name`")

	return frappe.get_all(
		"Serial and Batch Bundle",
		fields=fields,
		filters=filters,
		order_by="`tabSerial and Batch Entry`.`idx`",
	)

@frappe.whitelist()
def get_batch_qty(
	batch_no=None,
	warehouse=None,
	item_code=None,
	posting_date=None,
	posting_time=None,
	ignore_voucher_nos=None,
	for_stock_levels=False,
):
	"""Returns batch actual qty if warehouse is passed,
	        or returns dict of qty by warehouse if warehouse is None

	The user must pass either batch_no or batch_no + warehouse or item_code + warehouse

	:param batch_no: Optional - give qty for this batch no
	:param warehouse: Optional - give qty for this warehouse
	:param item_code: Optional - give qty for this item
	:param for_stock_levels: True consider expired batches"""

	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
		get_auto_batch_nos,
	)

	batchwise_qty = defaultdict(float)
	kwargs = frappe._dict(
		{
			"item_code": item_code,
			"warehouse": warehouse,
			"posting_date": posting_date,
			"posting_time": posting_time,
			"batch_no": batch_no,
			"ignore_voucher_nos": ignore_voucher_nos,
			"for_stock_levels": for_stock_levels,
		}
	)

	batches = get_auto_batch_nos(kwargs)

	for batch in batches:
		batchwise_qty[batch.get("batch_no")] += batch.get("qty")

	batch_details = frappe.db.get_value("Batch", batch_no, ["length", "width", "weight", "thickness", "custom_grade", "custom_tracking_no"], as_dict=1)

	details = frappe._dict({
		"batch_no": batch_no,
		"warehouse": warehouse,
		"qty": batchwise_qty[batch_no],
		"item_code": item_code,
	})

	details.update(batch_details)
	return details

def get_type_of_transaction(parent_doc, child_row):
	type_of_transaction = child_row.get("type_of_transaction")
	if parent_doc.get("doctype") == "Stock Entry":
		type_of_transaction = "Outward" if child_row.s_warehouse else "Inward"

	if not type_of_transaction:
		type_of_transaction = "Outward"
		if parent_doc.get("doctype") in ["Purchase Receipt", "Purchase Invoice"]:
			type_of_transaction = "Inward"

	if parent_doc.get("doctype") == "Subcontracting Receipt":
		type_of_transaction = "Outward"
		if child_row.get("doctype") == "Subcontracting Receipt Item":
			type_of_transaction = "Inward"
	elif parent_doc.get("doctype") == "Stock Reconciliation":
		type_of_transaction = "Inward"

	if parent_doc.get("is_return"):
		type_of_transaction = "Inward"
		if (
			parent_doc.get("doctype") in ["Purchase Receipt", "Purchase Invoice"]
			or child_row.get("doctype") == "Subcontracting Receipt Item"
		):
			type_of_transaction = "Outward"

	return type_of_transaction

def get_filters_for_bundle(item_code=None, docstatus=None, voucher_no=None, name=None, child_row=None):
	filters = [
		["Serial and Batch Bundle", "is_cancelled", "=", 0],
	]

	if child_row and isinstance(child_row, str):
		child_row = parse_json(child_row)

	if not name and child_row and child_row.get("qty") < 0:
		bundle = get_reference_serial_and_batch_bundle(child_row)
		if bundle:
			voucher_no = None
			filters.append(["Serial and Batch Bundle", "name", "=", bundle])

	if item_code:
		filters.append(["Serial and Batch Bundle", "item_code", "=", item_code])

	if not docstatus:
		docstatus = [0, 1]

	if isinstance(docstatus, list):
		filters.append(["Serial and Batch Bundle", "docstatus", "in", docstatus])
	else:
		filters.append(["Serial and Batch Bundle", "docstatus", "=", docstatus])

	if voucher_no:
		filters.append(["Serial and Batch Bundle", "voucher_no", "=", voucher_no])

	if name:
		if isinstance(name, list):
			filters.append(["Serial and Batch Entry", "parent", "in", name])
		else:
			filters.append(["Serial and Batch Entry", "parent", "=", name])

	return filters

def on_submit(doc, method=None):
	set_batch_details(doc)

def set_batch_details(doc):
	for row in doc.entries:
		if not row.batch_no:
			continue

		if doc.type_of_transaction == "Inward" and row.qty > 0:
			frappe.db.set_value("Batch", row.batch_no, {
				"length": row.length or 0,
				"width": row.width or 0,
				"weight": row.weight or 0,
				"thickness": row.thickness or 0,
				"custom_grade": row.custom_grade,
				"custom_tracking_no": row.custom_tracking_no,
			})

