
frappe.ui.form.on('Payment Order', {
	refresh(frm) {
		if (frm.doc.docstatus && frm.doc.status === 'Pending') {
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

			frm.trigger("custom_get_from_payment_entry");
		}, __("Get Payments from"));
	},

	custom_get_from_payment_entry(frm) {
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
				utr_no: ["is", "not set"]
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
		frm.add_custom_button('Upload File', () => {
			frm.trigger('prepare_dialog')
		});
	},

	prepare_dialog(frm) {
		frm.upload_file_dialog = new frappe.ui.Dialog({
			title: 'Upload File',
			fields: frm.events.get_fields(frm),
			size: 'extra-large',
			primary_action: (values) => {
				debugger
				frm.events.update_data(frm, values);
			},
			primary_action_label: __('Update')
		})

		frm.upload_file_dialog.show();
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
				if (r.message) {
					frm.upload_file_dialog.fields_dict.statement_data.df.data = [];
					r.message.forEach((data, index) => {
						if (index !== 0 && frm.upload_file_dialog.fields_dict.import_file.value) {
							frm.upload_file_dialog.fields_dict.statement_data.df.data.push({
								'reference_name': data[0],
								'company_bank_account': data[1],
								'posting_date': data[2],
								'amount': data[3],
								'paty_name': data[4],
								'ben_bank_name': data[10],
								'party_account_no': data[11],
								'utr_no': data[13],
								'utr_date': data[14]
							});
						}
					});

					frm.upload_file_dialog.fields_dict.statement_data.grid.refresh();
				}
			}
		})
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
				'label': 'Import File',
				'fieldname': 'import_file',
				'fieldtype': 'Attach',
				change: function() {
					frm.events.preview_uploaded_file(frm);
				}
			},
			{
				'label': 'Bank Statement',
				'fieldname': 'statement_data',
				'fieldtype': 'Table',
				'data': [],
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
						'fieldname': 'paty_name',
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
			}
		]
	}
})