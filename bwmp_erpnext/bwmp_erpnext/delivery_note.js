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

frappe.ui.form.on('Delivery Note Item', {
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


erpnext.show_serial_batch_selector = function (frm, d, callback, on_close, show_dialog) {
	let warehouse, receiving_stock, existing_stock;
	if (frm.doc.is_return) {
		if (["Purchase Receipt", "Purchase Invoice"].includes(frm.doc.doctype)) {
			existing_stock = true;
			warehouse = d.warehouse;
		} else if (["Delivery Note", "Sales Invoice"].includes(frm.doc.doctype)) {
			receiving_stock = true;
		}
	} else {
		if (frm.doc.doctype == "Stock Entry") {
			if (frm.doc.purpose == "Material Receipt") {
				receiving_stock = true;
			} else {
				existing_stock = true;
				warehouse = d.s_warehouse;
			}
		} else {
			existing_stock = true;
			warehouse = d.warehouse;
		}
	}

	if (!warehouse) {
		if (receiving_stock) {
			warehouse = ["like", ""];
		} else if (existing_stock) {
			warehouse = ["!=", ""];
		}
	}

	frappe.require("assets/bwmp_erpnext/js/serial_no_batch_selector.js", function() {
		new erpnext.SerialNoBatchSelector({
			frm: frm,
			item: d,
			warehouse_details: {
				type: "Warehouse",
				name: warehouse
			},
			callback: callback,
			on_close: on_close
		}, show_dialog);
	});
}


erpnext.stock.select_batch_and_serial_no = function(frm, item) {
	let get_warehouse_type_and_name = (item) => {
		let value = '';
		if(frm.fields_dict.from_warehouse.disp_status === "Write") {
			value = cstr(item.s_warehouse) || '';
			return {
				type: 'Source Warehouse',
				name: value
			};
		} else {
			value = cstr(item.t_warehouse) || '';
			return {
				type: 'Target Warehouse',
				name: value
			};
		}
	}

	if(item && !item.has_serial_no && !item.has_batch_no) return;
	if (frm.doc.purpose === 'Material Receipt') return;


	new erpnext.SerialNoBatchSelector({
		frm: frm,
		item: item,
		warehouse_details: get_warehouse_type_and_name(item),
	}, true);
}