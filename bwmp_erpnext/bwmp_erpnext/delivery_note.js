frappe.provide("erpnext.stock");

frappe.ui.form.on('Delivery Note', {
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

						frappe.require("assets/bwmp_erpnext/js/serial_no_batch_selector.js", function() {
                            erpnext.stock.select_batch_and_serial_no(frm, row);
                        });
					}
				}
			});
		}
	}
})
