// Copyright (c) 2016, IT2SME Co., Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Productie Voorraad Details"] = {
	"filters": [
        {
			"fieldname": "quotation_bom",
			"label": __("Quotation"),
			"fieldtype": "Data",
			"reqd": 1,
            "read_only": 1
		}, {
			"fieldname": "show_exploded_view",
			"label": __("Show exploded view"),
			"fieldtype": "Check",
            "default": "1",
            "read_only": 1
		}, {
			"fieldname": "qty_to_produce",
			"label": __("Quantity to Produce"),
			"fieldtype": "Int",
			"default": "1"
		 },
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.id == "Item"){
			if (data["Enough Parts to Build"] > 0){
				value = `<a style='color:green' href="#Form/Item/${data['Item']}" data-doctype="Item">${data['Item']}</a>`
			} else {
				value = `<a style='color:red' href="#Form/Item/${data['Item']}" data-doctype="Item">${data['Item']}</a>`
			}
		}
		return value
	}
}