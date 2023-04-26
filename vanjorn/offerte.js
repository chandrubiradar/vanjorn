frappe.ui.form.on('Sales Invoice', {
    before_submit: function(frm) {
        if(cur_frm.doc.klant_referentie) {
            frappe.call({
                type: "GET",
                method: "vanjorn.api.eind_factuur",
                args: {
                    "klant_referentie": cur_frm.doc.klant_referentie,
                    "posting_date": cur_frm.doc.posting_date,
                    "grand_total": cur_frm.doc.grand_total,
                    "btw": cur_frm.doc.total_taxes_and_charges*0.7,
                    "btwsoort": cur_frm.doc.taxes_and_charges,
                    "factuur_id": cur_frm.doc.name,
                },
                callback: function(r, rt) {
                    if(r.message.status===100){
                        console.log(r.message.description)
                        msgprint(r.message.description)
                    } else {
                        console.log(r.message.description)
                        msgprint(r.message.description)
                        validated = false;
                    }
                }
            });
        } else {
            frappe.call({
                type: "GET",
                method: "vanjorn.api.losse_factuur",
                args: {
                    "customer": cur_frm.doc.customer,
                    "posting_date": cur_frm.doc.posting_date,
                    "grand_total": cur_frm.doc.grand_total,
                    "net_total": cur_frm.doc.net_total,
                    "btw": cur_frm.doc.total_taxes_and_charges,
                    "btwsoort": cur_frm.doc.taxes_and_charges,
                    "factuur_id": cur_frm.doc.name,
                    "omzet_grootboek": cur_frm.doc.snelstart_grootboek
                },
                callback: function(r, rt) {
                    if(r.message.status===100){
                        console.log(r.message.description)
                        msgprint(r.message.description)
                    } else {
                        console.log(r.message.description)
                        msgprint(r.message.description)
                        validated = false;
                    }
                }
            });
        }
    } 
});

frappe.ui.form.on("Sales Invoice","validate", function(){
	frappe.call({                        
		method: "frappe.client.get_value", 
		args: { 
			doctype: "Quotation",
			fieldname: ["name"],
			filters: { lead: cur_frm.doc.lead_name, docstatus: 1},
			  },
			callback: function(r) {
			  if (r.message.name){
				  for (var i =0; i < cur_frm.doc.items.length; i++){
					  var row = cur_frm.doc.items[i];
					  row.item_image = "<img src='" + row.image + "' width='25' height='25'>";
				  }
				  cur_frm.refresh_field('items');
					var suma = 0;
					var sumb = 0;
					var sumi = 0;
					var sums = 0;
					var sumc = 0;
					$.each(cur_frm.doc.items, function(i, d) { 
						if(d.item_group==="Accessoires" && d.quotation == r.message.name) { 
							suma += d.amount
						}
						if(d.item_group==="Modules" && d.quotation == r.message.name) { 
							sumi += d.amount
						}
						if(d.item_group==="Basis" && d.quotation == r.message.name) { 
							sumb += d.amount
						}
						if(d.item_group==="Styling" && d.quotation == r.message.name) { 
							sums += d.amount
						}
						if(d.item_group==="Custom" && d.quotation == r.message.name) { 
							sumc += d.amount
						}
					});
					cur_frm.set_value("basis_bedrag", sumb);
					cur_frm.set_value("interieur_bedrag", sumi);
					cur_frm.set_value("accessoires_bedrag", suma);
					cur_frm.set_value("styling_bedrag", sums);
					cur_frm.set_value("custom_bedrag", sumc);
			} else {
				frappe.throw("Geen basis offerte gevonden voor deze factuur, probeer opnieuw!")
			}
		}
	});
});