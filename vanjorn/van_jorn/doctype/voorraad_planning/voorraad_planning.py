# -*- coding: utf-8 -*-
# Copyright (c) 2020, IT2SME Co., Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.utils import get_fetch_values
from frappe.model.mapper import get_mapped_doc
import frappe.utils
from frappe.utils import cstr, flt, getdate, comma_and, cint, nowdate, add_days

class VoorraadPlanning(Document):

    def get_items(self):
        self.set("items", [])
        self.delivery_date = frappe.utils.today()
        voorraad = frappe.db.sql(
            """
               SELECT
                GROUP_CONCAT(DISTINCT 'Offerte : ', qi.parent, ' Regel : ',qi.idx,' - <b>', ROUND(qi.qty-IFNULL(pi.complete_qty,0),2), ' X ', qi.item_name,'</b> - ', ' Aantal Onderdelen = <b>',ROUND(bi.stock_qty*(qi.qty-IFNULL(pi.complete_qty,0)),2), '</b> ID : <b><a href="/desk#Form/BOM/', bi.parent, '" target="_blank">', bi.parent, '</a></b>' ORDER BY qi.parent ASC SEPARATOR '<br>') as bom_item,
                bi.item_code as item_code,
                i.item_name as item_name,
                bi.stock_uom as stock_uom,
                MAX(if(i.purchase_uom IS NOT NULL,i.purchase_uom,bi.stock_uom)) as uom,
                MAX(if(i.purchase_uom IS NOT NULL and i.purchase_uom = c.uom, c.conversion_factor, 1)) as conversion_factor,
                i.safety_stock as safety_stock,
                i.min_order_qty as min_order_qty,
                SUM(bi.stock_qty*(qi.qty-IFNULL(pi.complete_qty,0))) as req_qty,
                
                CASE WHEN ((IF(MAX(s.actual_qty)>0,MAX(s.actual_qty),0)+IF(MAX(s.ordered_qty)>0,MAX(s.ordered_qty),0))
                    -(SUM(bi.stock_qty*(qi.qty-IFNULL(pi.complete_qty,0)))))< i.safety_stock
                
                THEN IF((ABS((IF(MAX(s.actual_qty)>0,MAX(s.actual_qty),0)+IF(MAX(s.ordered_qty)>0,MAX(s.ordered_qty),0))-(SUM(bi.stock_qty*(qi.qty-IFNULL(pi.complete_qty,0)))))+i.safety_stock
                    / MAX(if(i.purchase_uom IS NOT NULL and i.purchase_uom = c.uom, c.conversion_factor, 1))) < i.min_order_qty,i.min_order_qty,
                    CEIL((ABS((IF(MAX(s.actual_qty)>0,MAX(s.actual_qty),0)+IF(MAX(s.ordered_qty)>0,MAX(s.ordered_qty),0))-(SUM(bi.stock_qty*(qi.qty-IFNULL(pi.complete_qty,0)))))+i.safety_stock)
                    / MAX(if(i.purchase_uom IS NOT NULL and i.purchase_uom = c.uom, c.conversion_factor, 1))))
                
                ELSE 0 END as qty,
                
                IF(MAX(s.actual_qty)>0,MAX(s.actual_qty),0) as stock_qty,
                IF(MAX(s.ordered_qty)>0,MAX(s.ordered_qty),0) as order_qty,
                CONCAT("<div style='width: 100%%; color: white; text-align: center; background-color: ", 
                    CASE WHEN ((IF(MAX(s.actual_qty)>0,MAX(s.actual_qty),0)+IF(MAX(s.ordered_qty)>0,MAX(s.ordered_qty),0))
                    -(SUM(bi.stock_qty*(qi.qty-IFNULL(pi.complete_qty,0)))))<0 THEN "red" 
                    ELSE "green" END,"; font-size: 10px; font-weight: bold'>",ROUND(((IF(MAX(s.actual_qty)>0,MAX(s.actual_qty),0)+IF(MAX(s.ordered_qty)>0,MAX(s.ordered_qty),0))
                    -(SUM(bi.stock_qty*(qi.qty-IFNULL(pi.complete_qty,0))))),2),"</div>") as qty_status,
                MAX(si.supplier) as supplier,
                MAX(si.supplier_part_no) as supplier_part_no

                FROM 
                `tabBOM` b, `tabBOM Explosion Item` bi, `tabQuotation` q, `tabQuotation Item` qi
                LEFT JOIN 
                
                (SELECT SUM(qty) as complete_qty, quotation_item FROM `tabProductie Module` group by quotation_item) as pi ON pi.quotation_item = qi.name, `tabItem Supplier` si, `tabItem` i LEFT JOIN `tabBin` s ON i.name = s.item_code, `tabUOM Conversion Detail` c

                WHERE
                bi.parent = b.name
                and b.is_default = 1
                and b.is_active = 1
                and qi.docstatus = 1
                and q.voorraadplanning_compleet != 1
                and q.name = qi.parent
                and q.vj_status in ("Klant Aanbetaald","Klant besteld","In productie")
                and b.docstatus = 1
                and b.item = qi.item_code
                and i.name = bi.item_code
                and i.bakje_bakje != 1
                and i.item_group NOT IN ("HPL Onderdelen","Meubelstoffen","Gordijnstoffen","Vloer Onderdelen")
                and i.name = c.parent
                and c.uom = i.purchase_uom
                and i.name = si.parent
                and i.disabled != 1
                and (qi.qty-IFNULL(pi.complete_qty,0)) > 0
                
                group by bi.item_code
                order by 14 desc
            """,
            {},
            as_dict=1)

        for data in voorraad:
            self.append('items', {
                'bom_item': data.bom_item,
                'item_code': data.item_code,
                'item_name': data.item_name,
                'uom': data.uom,
                'stock_uom': data.stock_uom,
                'safety_stock': data.safety_stock,
                'min_order_qty': data.min_order_qty,
                'conversion_factor': data.conversion_factor,
                'req_qty': data.req_qty,
                'stock_qty': data.stock_qty,
                'order_qty': data.order_qty,
                'qty_status': data.qty_status,
                'qty': data.qty,
                'supplier': data.supplier,
                'supplier_part_no': data.supplier_part_no
            })

        bom_non_offerte_voorraad = frappe.db.sql(
            """
               SELECT
                i.name as item_code,
                i.item_name as item_name,
                i.stock_uom as stock_uom,
                i.purchase_uom as uom,
                IF(c.conversion_factor > 0,c.conversion_factor,1) as conversion_factor,
                i.min_order_qty as min_order_qty,
                SUM(b.ordered_qty) as ordered_qty,
                i.safety_stock as safety_stock,
                SUM(b.actual_qty) as stock_qty,
                IF((SUM(b.actual_qty) - i.safety_stock) > (i.min_order_qty*c.conversion_factor), 
                CEIL(ABS(SUM(b.actual_qty) - i.safety_stock)/c.conversion_factor),i.min_order_qty) as order_qty,
                MAX(si.supplier) as supplier,
                MAX(si.supplier_part_no) as supplier_part_no,
                CONCAT("<div style='width: 100%%; color: white; text-align: center; background-color: red; font-size: 10px; font-weight: bold'>",ROUND((SUM(b.actual_qty) - i.safety_stock),2),"</div>") as qty_status

                FROM 
                `tabItem Supplier` si, `tabItem` i, `tabBin` b, `tabUOM Conversion Detail` c

                WHERE
                i.name = c.parent
                and c.uom = i.purchase_uom
                and i.name = b.item_code
                and i.name = si.parent
                and i.is_stock_item = 1
                and i.safety_stock > 0
                and i.disabled != 1
                and i.bakje_bakje != 1
                and i.item_group NOT IN ("HPL Onderdelen","Meubelstoffen","Gordijnstoffen","Vloer Onderdelen")
                and NOT EXISTS (SELECT bi.item_code 
                                FROM `tabBOM Explosion Item` bi, `tabBOM` b
                                where bi.parent = b.name
                                and NOT EXISTS (SELECT qi.item_code FROM `tabQuotation Item` qi where qi.item_code = b.item and qi.docstatus = 1))
                and NOT EXISTS (SELECT bom.item FROM `tabBOM` bom where bom.item = i.name)

                group by i.name
                HAVING (SUM(b.actual_qty) - i.safety_stock) < 0

                order by 1 desc
            """,
            {},
            as_dict=1)

        for data in bom_non_offerte_voorraad:
            self.append('items', {
                'bom_item': data.bom_item,
                'item_code': data.item_code,
                'item_name': data.item_name,
                'uom': data.uom,
                'stock_uom': data.stock_uom,
                'safety_stock': data.safety_stock,
                'min_order_qty': data.min_order_qty,
                'conversion_factor': data.conversion_factor,
                'req_qty': data.req_qty,
                'stock_qty': data.stock_qty,
                'order_qty': data.ordered_qty,
                'qty_status': data.qty_status,
                'qty': data.order_qty,
                'supplier': data.supplier,
                'supplier_part_no': data.supplier_part_no
            })

        bom_non_stock_offerte_voorraad = frappe.db.sql(
            """
               SELECT
                i.name as item_code,
                i.item_name as item_name,
                i.stock_uom as stock_uom,
                i.purchase_uom as uom,
                IF(c.conversion_factor > 0,c.conversion_factor,1) as conversion_factor,
                i.min_order_qty as min_order_qty,
                0 as ordered_qty,
                i.safety_stock as safety_stock,
                0 stock_qty,
                IF((0 - i.safety_stock) > (i.min_order_qty*c.conversion_factor), 
                CEIL(ABS(0 - i.safety_stock)/c.conversion_factor),i.min_order_qty) as order_qty,
                MAX(si.supplier) as supplier,
                MAX(si.supplier_part_no) as supplier_part_no,
                CONCAT("<div style='width: 100%%; color: white; text-align: center; background-color: red; font-size: 10px; font-weight: bold'>",ROUND((0 - i.safety_stock),2),"</div>") as qty_status

                FROM 
                `tabItem Supplier` si, `tabItem` i, `tabUOM Conversion Detail` c

                WHERE
                i.name = c.parent
                and c.uom = i.purchase_uom
                and i.name = si.parent
                and i.is_stock_item = 1
                and i.safety_stock > 0
                and i.bakje_bakje != 1
                and (0 - i.safety_stock) < 0
                and i.item_group NOT IN ("HPL Onderdelen","Meubelstoffen","Gordijnstoffen","Vloer Onderdelen")
                AND NOT EXISTS (SELECT b.item_code FROM `tabBin` b where i.name = b.item_code)
                and i.disabled != 1
                and NOT EXISTS (SELECT bi.item_code 
                                FROM `tabBOM Explosion Item` bi, `tabBOM` b
                                where bi.parent = b.name
                                and NOT EXISTS (SELECT qi.item_code FROM `tabQuotation Item` qi where qi.item_code = b.item and qi.docstatus = 1))
                
                and NOT EXISTS (SELECT bom.item FROM `tabBOM` bom where bom.item = i.name)
                
                group by i.name

                order by 1 desc
            """,
            {},
            as_dict=1)

        for data in bom_non_stock_offerte_voorraad:
            self.append('items', {
                'bom_item': data.bom_item,
                'item_code': data.item_code,
                'item_name': data.item_name,
                'uom': data.uom,
                'stock_uom': data.stock_uom,
                'safety_stock': data.safety_stock,
                'min_order_qty': data.min_order_qty,
                'conversion_factor': data.conversion_factor,
                'req_qty': data.req_qty,
                'stock_qty': data.stock_qty,
                'order_qty': data.ordered_qty,
                'qty_status': data.qty_status,
                'qty': data.order_qty,
                'supplier': data.supplier,
                'supplier_part_no': data.supplier_part_no
            })

        veilig_heids_voorraad = frappe.db.sql(
            """
               SELECT
                i.name as item_code,
                i.item_name as item_name,
                i.stock_uom as stock_uom,
                i.purchase_uom as uom,
                IF(c.conversion_factor > 0,c.conversion_factor,1) as conversion_factor,
                i.min_order_qty as min_order_qty,
                SUM(b.ordered_qty) as ordered_qty,
                i.safety_stock as safety_stock,
                SUM(b.actual_qty) as stock_qty,
                IF((SUM(b.actual_qty) - i.safety_stock) > (i.min_order_qty*c.conversion_factor), 
                CEIL(ABS(SUM(b.actual_qty) - i.safety_stock)/c.conversion_factor),i.min_order_qty) as order_qty,
                MAX(si.supplier) as supplier,
                MAX(si.supplier_part_no) as supplier_part_no,
                CONCAT("<div style='width: 100%%; color: white; text-align: center; background-color: red; font-size: 10px; font-weight: bold'>",ROUND((SUM(b.actual_qty) - i.safety_stock),2),"</div>") as qty_status

                FROM  
                `tabItem Supplier` si, `tabItem` i, `tabBin` b, `tabUOM Conversion Detail` c

                WHERE
                i.name = c.parent
                and c.uom = i.purchase_uom
                and i.name = si.parent
                and i.is_stock_item = 1
                and i.safety_stock > 0
                and i.disabled != 1
                and i.name = b.item_code
                and i.item_group NOT IN ("HPL Onderdelen","Meubelstoffen","Gordijnstoffen","Vloer Onderdelen")
                and i.bakje_bakje = 1
                and NOT EXISTS (SELECT bom.item FROM `tabBOM` bom where bom.item = i.name)
                
                group by i.name
                HAVING (SUM(b.actual_qty) - i.safety_stock) < 0
                order by 1 desc
            """,
            {},
            as_dict=1)

        for data in veilig_heids_voorraad:
            self.append('items', {
                'bom_item': data.bom_item,
                'item_code': data.item_code,
                'item_name': data.item_name,
                'uom': data.uom,
                'stock_uom': data.stock_uom,
                'safety_stock': data.safety_stock,
                'min_order_qty': data.min_order_qty,
                'conversion_factor': data.conversion_factor,
                'req_qty': data.req_qty,
                'stock_qty': data.stock_qty,
                'order_qty': data.ordered_qty,
                'qty_status': data.qty_status,
                'qty': data.order_qty,
                'supplier': data.supplier,
                'supplier_part_no': data.supplier_part_no
            })

        non_stock_veilig_heids_voorraad = frappe.db.sql(
            """
               SELECT
                i.name as item_code,
                i.item_name as item_name,
                i.stock_uom as stock_uom,
                i.purchase_uom as uom,
                IF(c.conversion_factor > 0,c.conversion_factor,1) as conversion_factor,
                i.min_order_qty as min_order_qty,
                0 as ordered_qty,
                i.safety_stock as safety_stock,
                0 as stock_qty,
                IF((0 - i.safety_stock) > (i.min_order_qty*c.conversion_factor), 
                CEIL(ABS(0 - i.safety_stock)/c.conversion_factor),i.min_order_qty) as order_qty,
                MAX(si.supplier) as supplier,
                MAX(si.supplier_part_no) as supplier_part_no,
                CONCAT("<div style='width: 100%%; color: white; text-align: center; background-color: red; font-size: 10px; font-weight: bold'>",ROUND((0 - i.safety_stock),2),"</div>") as qty_status

                FROM  
                `tabItem Supplier` si, `tabItem` i, `tabUOM Conversion Detail` c

                WHERE
                i.name = c.parent
                and c.uom = i.purchase_uom
                and i.name = si.parent
                and i.is_stock_item = 1
                and i.safety_stock > 0
                and i.item_group NOT IN ("HPL Onderdelen","Meubelstoffen","Gordijnstoffen","Vloer Onderdelen")
                and i.disabled != 1
                and i.bakje_bakje = 1
                and (0 - i.safety_stock) < 0
                AND NOT EXISTS (SELECT b.item_code FROM `tabBin` b where i.name = b.item_code)
                and NOT EXISTS (SELECT bom.item FROM `tabBOM` bom where bom.item = i.name)
                
                group by i.name

                order by 1 desc
            """,
            {},
            as_dict=1)

        for data in non_stock_veilig_heids_voorraad:
            self.append('items', {
                'bom_item': data.bom_item,
                'item_code': data.item_code,
                'item_name': data.item_name,
                'uom': data.uom,
                'stock_uom': data.stock_uom,
                'safety_stock': data.safety_stock,
                'min_order_qty': data.min_order_qty,
                'conversion_factor': data.conversion_factor,
                'req_qty': data.req_qty,
                'stock_qty': data.stock_qty,
                'order_qty': data.ordered_qty,
                'qty_status': data.qty_status,
                'qty': data.order_qty,
                'supplier': data.supplier,
                'supplier_part_no': data.supplier_part_no
            })


@frappe.whitelist()
def make_purchase_order(source_name, for_supplier=None, target_doc=None):
    def set_missing_values(source, target):
        target.supplier = supplier
        target.apply_discount_on = ""
        target.additional_discount_percentage = 0.0
        target.discount_amount = 0.0

        default_price_list = frappe.get_value("Supplier", supplier, "default_price_list")
        if default_price_list:
            target.buying_price_list = default_price_list

        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")

    def update_item(source, target, source_parent):
        target.schedule_date = self.delivery_date
        target.qty = flt(source.qty)
        target.stock_qty = (flt(source.qty) - flt(source.qty)) * flt(source.conversion_factor)

    suppliers =[]
    self = frappe.get_doc("Voorraad Planning", "Voorraad Planning")
    for item in self.items:
        if item.supplier and item.supplier not in suppliers and item.qty > 0:
            suppliers.append(item.supplier)
    for supplier in suppliers:
        po = frappe.get_list("Purchase Order", filters={"transaction_date": self.delivery_date, "supplier": supplier, "docstatus": ("=", "0")})
        if len(po) == 0:
            doc = get_mapped_doc("Voorraad Planning", "Voorraad Planning", {
                "Voorraad Planning": {
                    "doctype": "Purchase Order",
                    "field_no_map": [
                        "address_display",
                        "contact_display",
                        "contact_mobile",
                        "contact_email",
                        "contact_person",
                        "taxes_and_charges",
                        "terms",
                        "tc_name"
                    ],
                    "field_map":  [
                        ["delivery_date", "schedule_date"]
                    ],
                },
                "Voorraad Artikelen": {
                    "doctype": "Purchase Order Item",
                    "field_map":  [
                        ["stock_uom", "stock_uom"],
                        ["uom", "uom"],
                        ["conversion_factor", "conversion_factor"],
                        ["delivery_date", "schedule_date"],
                        ["item_name", "description"]
                    ],
                    "field_no_map": [
                        "rate",
                        "price_list_rate",
                        "discount_percentage",
                        "discount_amount",
                        "supplier",
                        "pricing_rules"
                    ],
                    "postprocess": update_item,
                    "condition": lambda doc: doc.supplier == supplier and doc.qty > 0
                }
            }, target_doc, set_missing_values)
            doc.insert()
        else:
            suppliers =[]
    if suppliers:
        frappe.db.commit()
        return doc
    else:
        frappe.msgprint("PO already created for all items")