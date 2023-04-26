// Copyright (c) 2020, IT2SME Co., Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Voorraad Transactie', 'refresh', function(frm) {
	$('head').append(
	  "<script src=\'assets/js/barcodescan.js'></script>"
	);
	  $(document).scannerDetection({
		  timeBeforeScanTest: 200, // wait for the next character for upto 200ms
		  avgTimeByChar: 100, // it's not a barcode if a character takes longer than 100ms
		  onComplete: function(barcode, qty){
			frappe.call({                        
                method: "frappe.client.get_value", 
                args: { 
                    doctype: "Item",
                    fieldname: ["name", "item_name", "stock_uom", "warehouse"],
                    filters: { name: barcode, is_stock_item: 1 },
                },
                callback: function(res) {
                    console.log(res.message)
                    if (res.message) {
                        frappe.call({                        
                            method: "frappe.client.get_value", 
                            args: { 
                                doctype: "Bin",
                                fieldname: ["actual_qty"],
                                filters: { item_code: barcode, warehouse: res.message.warehouse },
                            },
                            callback: function(r) {
                                if (r.message) {
                                    var options = [];
                                    frappe.call({
                                        method: "frappe.client.get_list",
                                        args: {
                                        doctype: "UOM Conversion Detail",
                                        fields: ["uom"],
                                        filters: [["parent", "=", res.message.name]],
                                        group_by: "uom",
                                        order_by: "idx asc",
                                        limit_page_length: 20
                                        },
                                        callback: function(response){
                                            cur_frm.set_value("artikel", res.message.name);
                                            cur_frm.set_value("artikel_naam", res.message.item_name);
                                            cur_frm.set_value("stock_unit", res.message.stock_uom);
                                            cur_frm.set_value("locatie", res.message.warehouse);
                                            cur_frm.set_value("actual_qty", r.message.actual_qty);
                                            response.message.forEach(function(list) {
                                                var uom = list.uom;
                                                options.push({"value" : uom});
                                                cur_frm.set_df_property("unit", "options", options);
                                                refresh_field('unit');
                                            })
                                        }
                                    })
                                } else {
                                    msgprint("Deze artikel heeft geen voorraad voor deze transactie")
                                    validated = false;
                                }
                            }
                        })
                    } else {
                        msgprint("Geen geldige artikel gevonden voor deze barcode of dit artikel is geen voorraad artikel!<br>Barcode is : " + barcode)
                        validated = false;
                    }
                }
            })
		  },
		  onError: function(string, qty) {
			//   msgprint(string);
		}
	});
});

frappe.ui.form.on('Voorraad Transactie', {
    qty: function(frm) {
        if (frm.doc.qty > 0) {
            cur_frm.set_value("aantal", frm.doc.qty*frm.doc.conversion_factor);
        }
    },
    unit: function(frm) {
        frappe.call({                        
            method: "frappe.client.get_value", 
            args: { 
                doctype: "UOM Conversion Detail",
                fieldname: ["conversion_factor"],
                filters: { parent: frm.doc.artikel, uom: frm.doc.unit },
            },
            callback: function(res) {
                cur_frm.set_value("conversion_factor", res.message.conversion_factor);
            }
        })
    },
    before_submit: function(frm) {
        // Create stock entry
        let docs = [];
        let child = [];
        var purpose = "";
        var t_warehouse = "";
        var s_warehouse = "";
        if(frm.doc.transactie_type=="In") {
            purpose = "Material Receipt";
            t_warehouse = frm.doc.locatie;
        } else {
            purpose = "Material Issue";
            s_warehouse = frm.doc.locatie;
        }
        child.push ({
            item_code: frm.doc.artikel,
            item_name: frm.doc.artikel_naam,
            uom: frm.doc.stock_unit,
            stock_uom: frm.stock_unit,
            conversion_factor: 1,
            t_warehouse: t_warehouse,
            s_warehouse: s_warehouse,
            qty: frm.doc.qty*frm.doc.conversion_factor
        });

        docs.push({
            doctype: "Stock Entry",
            purpose: purpose,
            to_warehouse: t_warehouse,
            from_warhouse: s_warehouse,
            items: child
        });
        const funcs = docs.map((doc) => {
            frappe.call({
                method: "frappe.client.submit",
                args: {
                doc: doc // doc object
                },
                callback: function(r) {
                //callback script
                }
            });  
        });
    }
});