import frappe

from frappe.utils.data import evaluate_filters
from frappe.model.naming import parse_naming_series
from frappe.core.doctype.document_naming_rule.document_naming_rule import DocumentNamingRule

class CustomDocumentNamingRule(DocumentNamingRule):
	def apply(self, doc):
		'''
		Apply naming rules for the given document. Will set `name` if the rule is matched.
		'''
		if self.conditions:
			if not evaluate_filters(doc, [(self.document_type, d.field, d.condition, d.value) for d in self.conditions]):
				return

		counter = frappe.db.get_value(self.doctype, self.name, 'counter', for_update=True) or 0
		naming_series = parse_naming_series(self.prefix, doc=doc)

		doc.name = naming_series + ('%0'+str(self.prefix_digits)+'d') % (counter + 1)

		if doc.doctype in ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry"]:
			doc.document_naming_series = self.prefix

		frappe.db.set_value(self.doctype, self.name, 'counter', counter + 1)