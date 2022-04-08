import frappe, json
from frappe import _
from frappe.utils import format_date, today
from frappe.contacts.doctype.contact.contact import get_default_contact
from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import execute

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

		data.extend([ party_data.mop_short_form, party_data.beneficiary_code,
			party_data.bank_account_no, row.amount, row.supplier, '', '', '', '', '', '', '', '',
			party_data.reference_no, row.reference_name])

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

		if bill_no:
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

	columns, data = execute(filters)

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

	return [row.reference_name for row in payment_entries]

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
				"docstatus": ["=", 1]
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
		doc.document_naming_series = doc.naming_series