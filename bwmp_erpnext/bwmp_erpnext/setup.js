
frappe.ui.form.on('Payment Order', {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === 'Pending') {
			frm.trigger('generate_csv_file');
			frm.trigger('upload_csv_file');
		} else if (frm.doc.docstatus === 0) {
			frm.trigger('add_action_button');
		}
	},

	add_action_button(frm) {
		frm.clear_custom_buttons();

		frm.add_custom_button(__('Payment Entry'), function() {
			frm.doc.references = [];
			refresh_field('references');

			frm.trigger("get_ordered_payment_entries");
		}, __("Get Payments from"));
	},

	get_ordered_payment_entries(frm) {
		frappe.call({
			method: 'bwmp_erpnext.bwmp_erpnext.setup.get_ordered_payment_entries',
			callback: function(r) {
				if (r.message) {
					frm.events.custom_get_from_payment_entry(frm, r.message);
				}
			}
		})
	},

	custom_get_from_payment_entry(frm, skip_payment_entries) {
		erpnext.utils.map_current_doc({
			method: "bwmp_erpnext.bwmp_erpnext.setup.make_payment_order",
			source_doctype: "Payment Entry",
			target: frm,
			date_field: "posting_date",
			setters: {
				party: frm.doc.supplier || ""
			},
			get_query_filters: {
				bank: frm.doc.bank,
				docstatus: 1,
				bank_account: frm.doc.company_bank_account,
				paid_from: frm.doc.account,
				utr_no: ["is", "not set"],
				name: ["not in", skip_payment_entries]
			}
		});
	},

	generate_csv_file(frm) {
		frm.add_custom_button('Download File', () => {
			const w = window.open(
				frappe.urllib.get_full_url(`/api/method/bwmp_erpnext.bwmp_erpnext.setup.download_csv_file?
					&payment_order=${encodeURIComponent(frm.doc.name)}`)
			);
			if (!w) {
				frappe.msgprint(__("Please enable pop-ups"));
			}
		}).addClass('btn-primary');
	},

	upload_csv_file(frm) {
		frm.add_custom_button('Update UTR Details', () => {
			frm.trigger('prepare_dialog')
		});
	},

	prepare_dialog(frm) {
		frm.upload_file_dialog = new frappe.ui.Dialog({
			title: 'Update UTR',
			fields: frm.events.get_fields(frm),
			size: 'extra-large',
			primary_action: (values) => {
				frm.events.update_data(frm, values);
			},
			primary_action_label: __('Update UTR Details')
		})

		frm.upload_file_dialog.show();
	},

	update_data(frm, values) {
		frm.call({
			method: 'bwmp_erpnext.bwmp_erpnext.setup.update_payment_entry',
			args: {
				payment_order: frm.doc.name,
				data: values.statement_data
			},
			callback: function() {
				frm.upload_file_dialog.hide();
				frm.reload_doc();
			}
		})
	},

	get_fields(frm) {
		return [
			{
				'label': 'Bank Statement',
				'fieldname': 'statement_data',
				'fieldtype': 'Table',
				'cannot_delete_rows': 1,
				'cannot_add_rows': 1,
				'data': frm.events.get_data(frm),
				'fields': [
					{
						'label' : 'Voucher No',
						'fieldname': 'reference_name',
						'in_list_view': 1,
						'fieldtype': 'Data',
						'columns': 2,
						'read_only': 1
					},
					{
						'label' : 'Company Acc No',
						'fieldname': 'company_bank_account',
						'in_list_view': 1,
						'fieldtype': 'Data',
						'columns': 1,
						'read_only': 1
					},
					{
						'label' : 'Date',
						'fieldname': 'posting_date',
						'in_list_view': 1,
						'fieldtype': 'Date',
						'columns': 1,
						'read_only': 1
					},
					{
						'label' : 'Amount',
						'fieldname': 'amount',
						'in_list_view': 1,
						'fieldtype': 'Currency',
						'columns': 1,
						'read_only': 1
					},
					{
						'label' : 'Beneficiay Name',
						'fieldname': 'party_name',
						'in_list_view': 1,
						'fieldtype': 'Data',
						'columns': 1,
						'read_only': 1
					},
					{
						'label' : 'Ben. Bank Name',
						'fieldname': 'ben_bank_name',
						'in_list_view': 1,
						'fieldtype': 'Data',
						'columns': 1,
						'read_only': 1
					},
					{
						'label' : 'Ben. Account No',
						'fieldname': 'party_account_no',
						'in_list_view': 1,
						'fieldtype': 'Data',
						'columns': 1,
						'read_only': 1
					},
					{
						'label' : 'UTR No',
						'fieldname': 'utr_no',
						'in_list_view': 1,
						'fieldtype': 'Data',
						'columns': 1,
						'read_only': 1
					},
					{
						'label' : 'UTR Date',
						'fieldname': 'utr_date',
						'in_list_view': 1,
						'fieldtype': 'Date',
						'columns': 1,
						'read_only': 1
					}
				]
			},
			{
				'fieldtype': 'Section Break'
			},
			{
				'label': 'Download File',
				'fieldname': 'download_file',
				'fieldtype': 'Button',
				click: function() {
					frm.events.download_file(frm);
				}
			},
			{
				'fieldtype': 'Section Break'
			},
			{
				'label': 'Upload File',
				'fieldname': 'import_file',
				'fieldtype': 'Attach',
				change: function() {
					frm.events.preview_uploaded_file(frm);
				}
			}
		]
	},

	download_file(frm) {
		let data = [['Voucher No', 'Company Acc No', 'Date', 'Amount', 'Beneficiay Name',
			'Ben. Bank Name', 'Ben. Account No', 'UTR No', 'UTR Date']];

		frm.upload_file_dialog.fields_dict.statement_data.df.data.forEach(row => {
			data.push([row.reference_name, row.company_bank_account, row.posting_date,
				row.amount, row.party_name, row.ben_bank_name, row.party_account_no, '', '']);
		});

		frappe.tools.downloadify(data, null, frm.doc.name + ' _update_utr_details');
	},

	get_data(frm) {
		let data = [];
		frm.doc.references.forEach(row => {
			data.push({
				'reference_name': row.reference_name,
				'company_bank_account': frm.doc.company_bank_account,
				'posting_date': frm.doc.posting_date,
				'amount': row.amount,
				'party_name': row.party_name,
				'ben_bank_name': row.bank_name,
				'party_account_no': row.party_account_no
			});
		});

		return data;
	},

	preview_uploaded_file(frm) {
		let file_name = (
			frm.upload_file_dialog.fields_dict.import_file.file_uploader.uploader.files[0].doc.name
		);

		frm.call({
			method: 'bwmp_erpnext.bwmp_erpnext.setup.import_uploaded_file',
			args: {
				payment_order: frm.doc.name,
				file_name: file_name
			},
			callback: function(r) {
				if (r.message && r.message.length) {
					frm.upload_file_dialog.fields_dict.statement_data.df.data = [];
					r.message.forEach((data, index) => {
						if (index !== 0 && frm.upload_file_dialog.fields_dict.import_file.value) {
							frm.upload_file_dialog.fields_dict.statement_data.df.data.push({
								'reference_name': data[0],
								'company_bank_account': data[1],
								'posting_date': data[2],
								'amount': data[3],
								'party_name': data[4],
								'ben_bank_name': data[5],
								'party_account_no': data[6],
								'utr_no': data[7],
								'utr_date': data[8]
							});
						}
					});

					frm.upload_file_dialog.fields_dict.statement_data.grid.refresh();
				}
			}
		})
	},
})