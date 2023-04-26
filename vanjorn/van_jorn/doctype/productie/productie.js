// Copyright (c) 2022, IT2SME Co., Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Productie', {
    refresh: function(frm) {
        if(cur_frm.doc.__islocal) {
            frm.page.set_secondary_action(__("Haal bestelde modules op"), function() {
                return frappe.call({
                    method: "get_modules",
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: "Moment geduld, data wordt opgehaald.",
                    callback: function(r, rt) {
                        frm.refresh_fields();
                        frm.page.clear_secondary_action();
                    }
                });
            });
        }
        if(!cur_frm.doc.__islocal && cur_frm.doc.docstatus==0) {
            frm.page.set_secondary_action(__("Check Voorraad"), function() {
                return frappe.call({
                    method: "check_voorraad",
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: "Moment geduld, Voorraad wordt berekend.",
                    callback: function(r, rt) {
                        cur_frm.save();
                    }
                });
            });
        }
    }
});

frappe.ui.form.on("Productie Module", {
    voorraad_details: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        // frappe.set_route("query-report", "Productie Voorraad Details", {"bom": d.bom, "quotation": d.offerte, "show_exploded_view": 1, "qty_to_produce": 1});
        frappe.set_route('query-report', 'Productie Voorraad Details', {quotation_bom: d.offerte + "&" + d.bom});
    }
});