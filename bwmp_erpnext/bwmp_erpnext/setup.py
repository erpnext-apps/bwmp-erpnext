import frappe, json
from frappe import _
from collections import OrderedDict
from frappe.utils import cint, flt, get_table_name, getdate, format_date, today
from pypika import functions as fn
from frappe.contacts.doctype.contact.contact import get_default_contact
from erpnext.stock.doctype.warehouse.warehouse import apply_warehouse_filter

from frappe.utils.csvutils import (
	build_csv_response,
	read_csv_content
)

from frappe.utils.xlsxutils import (
	read_xlsx_file_from_attached_file,
	read_xls_file_from_attached_file
)


@frappe.whitelist()
def download_csv_file(payment_order):
	csv_data = []
	doc = frappe.get_doc('Payment Order', payment_order)

	for row in doc.references:
		data = []

		party_data = get_bank_and_payment_details(row.bank_account, row.reference_name)

		neft_reference_no = (row.reference_name
			if party_data.mode_of_payment == 'NEFT' else party_data.reference_no)

		data.extend([ party_data.mop_short_form, party_data.beneficiary_code,
			party_data.bank_account_no, row.amount, row.supplier, '', '', '', '', '', '', '', '',
			neft_reference_no, row.reference_name])

		data.extend(get_supplier_invoice_no(row, party_data))

		data.extend([doc.posting_date, '',
			party_data.ifsc_code, party_data.bank, party_data.branch_name,
			party_data.email
		])

		csv_data.append(data)

	date_format = parse_naming_series('YYYY.MM.DD', doc.posting_date)
	filename = f'{payment_order}-{date_format}'
	build_csv_response(csv_data, filename)

def get_supplier_invoice_no(row, party_data):
	data = ['', '', '', '', '', '', '']

	if row.reference_doctype == 'Payment Entry':
		index = 0
		references = frappe.get_all('Payment Entry Reference',
			filters = {'parent': row.reference_name, 'bill_no': ['is', 'set']},
			fields=['bill_no'], order_by="idx")

		bill_no = ''
		for reference in references:
			if index == 7:
				continue

			if len(bill_no) + len(reference.bill_no) < 29:
				bill_no += reference.bill_no + ', '
			elif bill_no:
				data[index] = bill_no
				bill_no = reference.bill_no
				index += 1

		if bill_no and len(data) > index:
			data[index] = bill_no

	return data

def get_bank_and_payment_details(bank_account, reference_name) -> list:
	bank_account = frappe.db.get_value('Bank Account', bank_account, ['beneficiary_code',
			'bank_account_no', 'reference_no', 'ifsc_code', 'bank', 'branch_name', 'email_id'], as_dict=1)

	payment_entry_details = frappe.db.get_value('Payment Entry', reference_name,
		['mode_of_payment', 'contact_email', 'party', 'party_type'], as_dict=1)

	bank_account.email = payment_entry_details.contact_email
	if payment_entry_details.party_type == 'Supplier':
		default_contact = get_default_contact('Supplier', payment_entry_details.party)
		email = get_default_contact_email(default_contact)
		if email:
			bank_account.email = email

	bank_account.mop_short_form = ''
	if payment_entry_details.mode_of_payment:
		bank_account.mop_short_form = frappe.get_cached_value('Mode of Payment',
			payment_entry_details.mode_of_payment, 'short_name')

	bank_account.mode_of_payment = payment_entry_details.mode_of_payment

	return bank_account

def get_default_contact_email(default_contact) -> str:
	"""
		Returns default contact for the given doctype and name.
		Can be ordered by `contact_type` to either is_primary_contact or is_billing_contact.
	"""
	out = frappe.db.sql("""
			SELECT
				email_id
			FROM
				`tabContact Email`
			WHERE
				parent=%s
			ORDER BY is_primary DESC
		""", (default_contact))
	if out:
		try:
			return out[0][0]
		except Exception:
			return None
	else:
		return None

@frappe.whitelist()
def update_payment_entry(payment_order, data):
	if isinstance(data, str):
		data = json.loads(data)

	for row in data:
		frappe.db.set_value('Payment Entry', row.get('reference_name'), {
			'utr_no': row.get('utr_no'),
			'utr_date': format_date(row.get('utr_date'), 'yyyy-mm-dd')
		})

	frappe.db.set_value('Payment Order', payment_order, 'status', 'Completed')

@frappe.whitelist()
def import_uploaded_file(payment_order, file_name):
	file_doc = frappe.get_doc("File", file_name)
	content = file_doc.get_content()
	parts = file_doc.get_extension()
	extension = parts[1].lstrip(".")

	return read_content(content, extension)

def read_content(content, extension):
	error_title = _("Template Error")
	if extension not in ("csv", "xlsx", "xls"):
		frappe.throw(
			_("Import template should be of type .csv, .xlsx or .xls"), title=error_title
		)

	if extension == "csv":
		data = read_csv_content(content)
	elif extension == "xlsx":
		data = read_xlsx_file_from_attached_file(fcontent=content)
	elif extension == "xls":
		data = read_xls_file_from_attached_file(content)

	return data

def unlink_uat_no_and_uat_date(doc, method):
	for row in doc.references:
		frappe.db.set_value('Payment Entry', row.get('reference_name'), {
			'utr_no': None,
			'utr_date': None
		})

def validate_payment_order(doc, method):
	if doc.docstatus == 0:
		doc.status = 'Pending'

@frappe.whitelist()
def get_available_batches(item_code, warehouse, company):
	filters = frappe._dict({
		"item_code": item_code,
		"warehouse": warehouse,
		"company": company,
		"from_date": today(),
		"to_date": today()
	})

	data = execute(filters)

	batch_wise_data = get_batch_details()
	for row in data:
		batch_data = batch_wise_data.get(row[4]) or frappe._dict()
		row.extend([batch_data.length, batch_data.width, batch_data.thickness, batch_data.weight])

	return data

def get_batch_details():
	batch_details = {}
	batch_data = frappe.get_all('Batch',
		fields=["name", "length", "width", "thickness", "weight"])

	for row in batch_data:
		batch_details[row.name] = row

	return batch_details

@frappe.whitelist()
def get_ordered_payment_entries():
	payment_entries = frappe.get_all('Payment Order',
		fields = ['`tabPayment Order Reference`.`reference_name`'],
		filters= [
			['Payment Order', 'status', '!=', 'Completed'],
			['Payment Order Reference', 'docstatus', '<', 2],
			['Payment Order Reference', 'reference_doctype', '=', 'Payment Entry']
		])

	return list(set([row.reference_name for row in payment_entries]))

@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc
	def set_missing_values(source, target):
		target.payment_order_type = "Payment Entry"
		target.append('references', dict(
			reference_doctype="Payment Entry",
			reference_name=source.name,
			bank_account=source.party_bank_account,
			amount=source.paid_amount,
			account=source.paid_to,
			supplier=source.party,
			mode_of_payment=source.mode_of_payment,
		))

	doclist = get_mapped_doc("Payment Entry", source_name, {
		"Payment Entry": {
			"doctype": "Payment Order",
			"validation": {
				"docstatus": ["=", 1],
				"name": ["not in", get_ordered_payment_entries()]
			},
			"field_no_map": [
				'posting_date',
				'status'
			]
		}

	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def has_batch_serial_no(item_code):
	return frappe.get_cached_value('Item', item_code, ['has_batch_no', 'has_serial_no'], as_dict=1)

def parse_naming_series(parts, date=None):
	n = ''
	if isinstance(parts, str):
		parts = parts.split('.')
	series_set = False
	today = date or now_datetime()
	for e in parts:
		part = ''
		if e.startswith('#'):
			if not series_set:
				digits = len(e)
				part = getseries(n, digits)
				series_set = True
		elif e == 'YY':
			part = today.strftime('%y')
		elif e == 'MM':
			part = today.strftime('%m')
		elif e == 'DD':
			part = today.strftime("%d")
		elif e == 'YYYY':
			part = today.strftime('%Y')
		elif e == 'WW':
			part = determine_consecutive_week_number(today)
		elif e == 'timestamp':
			part = str(today)
		elif e == 'FY':
			part = frappe.defaults.get_user_default("fiscal_year")
		elif e.startswith('{') and doc:
			e = e.replace('{', '').replace('}', '')
			part = doc.get(e)
		elif doc and doc.get(e):
			part = doc.get(e)
		else:
			part = e

		if isinstance(part, str):
			n += part

	return n

def update_naming_prefix(doc, method):
	if doc.doctype in ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry"]:
		if not doc.document_naming_series:
			doc.document_naming_series = doc.naming_series

	if doc.doctype == 'Payment Entry':
		if doc.mode_of_payment == "NEFT":
			doc.reference_no = doc.name
			doc.reference_date = today()


def execute(filters=None):
	if not filters:
		filters = {}

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	float_precision = cint(frappe.db.get_default("float_precision")) or 3
	iwb_map = get_item_warehouse_batch_map(filters, float_precision)

	data = []
	for key, details in iwb_map.items():
		if flt(details.bal_qty, 3) <= 0:
			continue

		data.append(
			[
				details.item_code,
				details.item_name,
				details.description,
				details.warehouse,
				details.batch_no,
				flt(details.bal_qty),
				flt(details.bal_qty),
				flt(details.bal_qty),
				flt(details.bal_qty),
				details.stock_uom,
			]
		)

	return data

def get_item_warehouse_batch_map(filters, float_precision):
	sle = get_stock_ledger_entries(filters)
	iwb_map = OrderedDict()

	for d in sle:
		key  = (d.item_code, d.warehouse, d.batch_no)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict({
				"bal_qty": 0,
				"item_code": d.item_code,
				"warehouse": d.warehouse,
				"batch_no": d.batch_no,
				"stock_uom": d.stock_uom,
				"item_name": d.item_name,
				"description": d.description,
				"posting_date": d.posting_date,
			})

		iwb_map[key]["bal_qty"] += flt(d.actual_qty, float_precision)

	return iwb_map


def get_stock_ledger_entries(filters):
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))
	if not filters.get("to_date"):
		frappe.throw(_("'To Date' is required"))

	sle = frappe.qb.DocType("Stock Ledger Entry")
	batch = frappe.qb.DocType("Batch")
	query = (
		frappe.qb.from_(sle)
		.inner_join(batch)
		.on(sle.batch_no == batch.name)
		.select(
			sle.item_code,
			sle.warehouse,
			sle.batch_no,
			sle.posting_date,
			batch.stock_uom,
			batch.item_name,
			batch.description,
			fn.Sum(sle.actual_qty).as_("actual_qty"),
		)
		.where(
			(sle.docstatus < 2)
			& (sle.is_cancelled == 0)
			& (fn.IfNull(sle.batch_no, "") != "")
			& (sle.posting_date <= filters["to_date"])
		)
		.groupby(sle.voucher_no, sle.batch_no, sle.item_code, sle.warehouse)
		.orderby(batch.creation)
	)

	if frappe.db.exists("Warehouse", filters.get("warehouse")):
		query = apply_warehouse_filter(query, sle, filters)

	for field in ["item_code", "batch_no", "company"]:
		if filters.get(field):
			query = query.where(sle[field] == filters.get(field))

	return query.run(as_dict=True)
