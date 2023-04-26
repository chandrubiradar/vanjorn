// Copyright (c) 2020, IT2SME Co., Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Voorraad Planning", "refresh", function(frm){
      frm.add_custom_button(__('Haal Data van openstaande Offertes'), function(){
        frappe.call({
          method: "get_items",
          doc: frm.doc,
          freeze: true,
          freeze_message: "Moment geduld, data wordt opgehaald.",
          callback: function(r, rt) {
            cur_frm.refresh_fields();
            cur_frm.save();
          }
        });
    });
});

frappe.ui.form.on("Voorraad Planning", "refresh", function(frm){
      frm.add_custom_button(__('Maak Bestelling'), function(){
        frappe.call({
        type: "GET",
        method: "vanjorn.van_jorn.doctype.voorraad_planning.voorraad_planning.make_purchase_order",
        args: {
            "source_name": cur_frm.doc.name,
            "for_supplier": ""
        },
        freeze: true,
        freeze_message: "Moment geduld, bestellingen worden aangemaakt.",
        callback: function(r, rt) {
            frappe.msgprint("Alle bestellingen zijn aagemaakt!");
        }
        });
    });
});
