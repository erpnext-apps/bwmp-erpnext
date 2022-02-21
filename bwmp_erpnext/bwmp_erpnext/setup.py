import frappe, json
from frappe import _
from frappe.utils import format_date

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
	csv_data = [['Txn Type', 'Beneficiary Code', 'Beneficiary A/c No', 'Amount', 'Beneficiary Name', '','', '',
		'', '', '', '', '', 'Customer Reference No', 'Payment Detail 1', 'Payment Detail 2','Payment Detail 3',
		'Payment Detail 4', 'Payment Detail 5', 'Payment Detail 6', 'Payment Detail 7','','Transaction Date',
		'', 'IFSC Code', 'Beneficiary Bank Name', 'Beneficiary Bank Branch Name', 'Beneficiary Email ID']]
	doc = frappe.get_doc('Payment Order', payment_order)

	for row in doc.references:
		data = ['']

		bank_account = frappe.db.get_value('Bank Account', row.bank_account, ['beneficiary_code',
			'bank_account_no', 'reference_no', 'ifsc_code', 'bank', 'branch_name', 'email_id'], as_dict=1)

		data.extend([bank_account.beneficiary_code, bank_account.bank_account_no,
			row.amount, row.supplier, '', '', '', '', '', '', '', '', bank_account.reference_no,
			row.reference_name, '', '', '', '', '', '', '', doc.posting_date, '',bank_account.ifsc_code, bank_account.bank,
			bank_account.branch_name, bank_account.email_id])

		csv_data.append(data)

	build_csv_response(csv_data, payment_order)

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
def has_batch_no(item_code):
	return frappe.get_cached_value('Item', item_code, 'has_batch_no')