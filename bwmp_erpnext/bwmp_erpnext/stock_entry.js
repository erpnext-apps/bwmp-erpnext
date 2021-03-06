frappe.provide("erpnext.stock");

frappe.ui.form.on('Stock Entry', {
	refresh(frm) {
		frm.trigger('hide_batch_selector');
	},

	stock_entry_type(frm) {
		frm.trigger('hide_batch_selector');
	},

	hide_batch_selector(frm) {
		frappe.flags.hide_serial_batch_dialog = true;
	},

	setup_batch_serial_no_selector(frm, row) {
		if (row.item_code && row.s_warehouse) {
			frappe.call({
				method: 'bwmp_erpnext.bwmp_erpnext.setup.has_batch_serial_no',
				args: {
					item_code: row.item_code
				},
				callback: function(r) {
					if (r.message) {
						row.has_batch_no = r.message.has_batch_no;
						row.has_serial_no = r.message.has_serial_no;

						if (frm.doc.stock_entry_type === 'Item Batch Splitting') {
							erpnext.stock.custom_batch_selector(frm, row);
						} else {
							frappe.require("assets/bwmp_erpnext/js/serial_no_batch_selector.js", function() {
								erpnext.stock.select_batch_and_serial_no(frm, row);
							});
						}
					}
				}
			});
		}
	}
})

frappe.ui.form.on('Stock Entry Detail', {
	item_code(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.flags.hide_serial_batch_dialog = true;
		frm.events.setup_batch_serial_no_selector(frm, row);
	},

	pick_batch_no(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.flags.hide_serial_batch_dialog = true;
		frm.events.setup_batch_serial_no_selector(frm, row);
	}
})

erpnext.stock.custom_batch_selector = (frm, item) => {
	frm.batch_selector_dialog = new frappe.ui.Dialog({
		title: __('Batch Selector'),
		fields: [
			{
				'label': 'Warehouse',
				'fieldname': 'warehouse',
				'fieldtype': 'Link',
				'options': 'Warehouse',
				'default': item.s_warehouse,
				change: function() {
					let warehouse = this.get_value();

					if (warehouse) {
						frm.batch_selector_dialog.fields_dict
							.batch_no.set_value('');
					}
				}
			},
			{
				'fieldtype': 'Column Break'
			},
			{
				'label': 'Batch',
				'fieldname': 'batch_no',
				'fieldtype': 'Link',
				'options': 'Batch',
				'default': item.batch_no,
				'get_query': function() {
					let warehouse = frm.batch_selector_dialog.fields_dict
						.warehouse.get_value();

					return {
						filters: {
							item_code: item.item_code,
							warehouse: warehouse
						},
						query: 'erpnext.controllers.queries.get_batch_no'
					};
				},
				change: function() {
					let batch_no = this.get_value();
					let warehouse = frm.batch_selector_dialog.fields_dict
						.warehouse.get_value();

					frappe.call({
						method: 'erpnext.stock.doctype.batch.batch.get_batch_qty',
						args: {
							batch_no,
							warehouse: warehouse,
							item_code: item.item_code
						},
						callback: (r) => {
							frm.batch_selector_dialog.fields_dict
								.qty.set_value(r.message || 0);
						}
					});
				}
			},
			{
				'fieldtype': 'Column Break'
			},
			{
				'label': 'Available Qty',
				'fieldname': 'qty',
				'fieldtype': 'Float',
				'read_only': 1
			}
		],
		primary_action: (values) => {
			frappe.model.set_value(item.doctype, item.name, {
				's_warehouse': values.warehouse,
				'qty': values.qty,
				'batch_no': values.batch_no
			});

			refresh_field("items");
			frm.batch_selector_dialog.hide();
		},
		primary_action_label: __('Update')
	});

	frm.batch_selector_dialog.show();
}