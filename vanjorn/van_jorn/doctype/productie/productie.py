# -*- coding: utf-8 -*-
# Copyright (c) 2022, IT2SME Co., Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
import frappe
import frappe.handler
import frappe.client
from frappe.utils.response import build_response
from frappe import _
from six.moves.urllib.parse import urlparse, urlencode
import base64
import requests
import json


class Productie(Document):

    def before_submit(self):
        self.create_stock_entry()
  
    def create_stock_entry(self):
        try:
            comment = ""
            for m in self.productie_module:
                if m.qty > 0 and m.verwerkt != 1:
                    raw_material = frappe.db.sql(
                            """ select
                                    b.item_code,
                                    ROUND(b.stock_qty*%(qty)s,2) as qty,
                                    i.warehouse,
                                    b.stock_uom,
                                    b.stock_qty,
                                    b.stock_uom,
                                    b.rate,
                                    IF(i.has_batch_no = 1,CONCAT(q.klant_referentie,"-",i.name,"-",q.hpl_variant),"") as batch_no
                                
                                FROM `tabBOM Explosion Item` b, `tabBOM` bom, `tabItem` i, `tabQuotation` q

                                WHERE
                                    b.parent = bom.name
                                    and i.name = b.item_code
                                    and i.is_stock_item = 1
                                    and bom.docstatus = 1
                                    and i.sub_assembly_voorraad != 1
                                    and i.bakje_bakje != 1
                                    and bom.is_default = 1
                                    and bom.is_active = 1
                                    and bom.item = %(item)s
                                    and q.name = %(quotation)s
                                
                                order by b.idx

                            """, {"quotation": m.offerte, "item": m.item_code, "qty": m.qty}, as_dict=1)

                    raw_material_twee = frappe.db.sql(
                            """ select
                                    b.item_code,
                                    ROUND(b.stock_qty*%(qty)s,2) as qty,
                                    i.warehouse,
                                    b.stock_uom,
                                    b.stock_qty,
                                    b.stock_uom,
                                    b.rate,
                                    IF(i.has_batch_no = 1,CONCAT(q.klant_referentie,"-",i.name,"-",q.hpl_variant),"") as batch_no
                                
                                FROM `tabBOM Item` b, `tabBOM` bom, `tabItem` i, `tabQuotation` q

                                WHERE
                                    b.parent = bom.name
                                    and i.name = b.item_code
                                    and i.is_stock_item = 1
                                    and i.sub_assembly_voorraad = 1
                                    and i.bakje_bakje != 1
                                    and bom.docstatus = 1
                                    and bom.is_default = 1
                                    and bom.is_active = 1
                                    and bom.item = %(item)s
                                    and q.name = %(quotation)s
                                
                                order by b.idx

                            """, {"quotation": m.offerte, "item": m.item_code, "qty": m.qty}, as_dict=1)

                    stock_items = []
                    bom_no = frappe.get_value('BOM', {"item": m.item_code, "is_default": 1, "docstatus": 1, "is_active": 1}, "name")

                    if bom_no:
                        for rm in raw_material:
                            stock = {
                                "item_code": rm.item_code,
                                "qty": rm.qty,
                                "basic_rate": rm.rate,
                                "uom": rm.uom,
                                "stock_qty": rm.stock_qty,
                                "conversion_factor": 1,
                                "stock_uom": rm.stock_uom,
                                "s_warehouse": rm.warehouse,
                                "batch_no": rm.batch_no
                            }
                            stock_items.append(stock)

                        for rm in raw_material_twee:
                            stock_twee = {
                                "item_code": rm.item_code,
                                "qty": rm.qty,
                                "basic_rate": rm.rate,
                                "uom": rm.uom,
                                "stock_qty": rm.stock_qty,
                                "conversion_factor": 1,
                                "stock_uom": rm.stock_uom,
                                "s_warehouse": rm.warehouse,
                            }
                        
                            stock_items.append(stock_twee)


                        sle = frappe.get_doc({
                            'doctype': 'Stock Entry',
                            'docstatus': 1,
                            'purpose': "Material Issue",
                            'remark': "Product ID : " + self.name,
                            'from_bom': 1,
                            'bom_no': bom_no,
                            'fg_completed_qty': m.qty,
                            'use_multi_level_bom': 0,
                            'items' : stock_items
                            })
                        sle.insert(ignore_permissions=True)
                        frappe.db.commit()

                        updatestock = frappe.get_doc('Productie Module', m.name)
                        updatestock.status = '<span class="indicator green"><span class="hidden-xs">Verwerkt</span></span>'
                        updatestock.verwerkt = 1
                        updatestock.save()
                        frappe.db.commit()

                        #--------------------create snelstart memoriaal-----------------------
                        url = "https://auth.snelstart.nl/b2b/token"

                        payload='grant_type=clientkey&clientkey=NzJ2d0RqSzVFcnZ4NkVwOTZMUU9QYUNJVGgwcGMvdEJUMWtjeFMyVUtXUlV1SWYyOXVyQnluYlNWdmxlRC9tTlJjazFhV1dBWXVLMUpzT3Evd1dDR3AyTU5BNW5vTXZmdFpCNTJIVmUwRjYyelFGNGxBZlk1M0cvVEMrL1FzK0lkK1FhbTVDRHVJaE4zOXFCL2ZrMldpVTlUTGtFTCt5RkNaNEVaRDFFOWNqQnloeGVpNjFYY0JpcmNOVEVIV1djNlkxdU82Rk5oUCt5TVh1eFJjNktOOGNyS2tTdU9KdUtpZzQ0dG5rSWM0dDhyazE5MlpnTWtFekt1d201SG9ZaDpvSE1ickZnRmZTUC9Bd2xYNGhNVzdOcTV0Q0kvYWhGck5UV2FtdG1JRU5pcXBMSDhnK1dDUS9FLzNoankvNnhwQWhBZTBrUFpDTmxOYUhja0gzRUR5MGMzQ09Gb295VVpVUzJzS0hDQXlKWitEZXNadnF1MTNHb1Fwc1NrZklSZ1dhdldvU3dmUkc3eHVyem5MZW5oUVp1RjlnRHNtL05paEJUbGtZVUxna2xWSnNCejhMKzBWdWQyeXo3ZDd5VjFLM2pXbDJqYWNjam8rZlpLUzI2bG05SUtzYkZDNlNBQ0MzaFNRcnNNbDJ5YVhGcGF4a0E0Qk8vWXoxcHg5SThP'
                        headers = {
                        'Content-Type': 'application/x-www-form-urlencoded'
                        }

                        response = requests.request("POST", url, headers=headers, data=payload)

                        snelstart = json.loads(response.text)
                        token = snelstart["access_token"]

                        #---------- memoriaal voorraad uitboeken --------------------
                        klant_referentie = frappe.get_value('Quotation', {'name': m.offerte}, 'klant_referentie')
                        module_naam = frappe.get_value('Quotation Item', {'name': m.quotation_item}, 'item_name')
                        kostenplaats = frappe.get_value('Lead', {'configurator_id': klant_referentie}, 'snelstart_kostenplaats')

                        url = "https://b2bapi.snelstart.nl/v2/memoriaalboekingen"

                        payload = json.dumps({
                            "datum": sle.posting_date,
                            "boekstuk": sle.name,
                            "omschrijving": module_naam + " Ref: " + klant_referentie,
                            "memoriaalBoekingsRegels": [
                                {
                                "omschrijving": module_naam + " Ref: " + klant_referentie,
                                "grootboek": {
                                    "id": "fd7fb057-7d38-484b-9143-96f31eaae82b"
                                },
                                "debet": 0.0,
                                "credit": sle.total_outgoing_value
                                },
                            ],
                            "dagboek": {
                                "id": "20bebb15-edf9-4b99-b960-95eae9bd509b"
                            }
                        })
                        headers = {
                        'Authorization': 'Bearer ' + token,
                        'Ocp-Apim-Subscription-Key': '9f637ff672984cb69298211844d36069',
                        'Content-Type': 'application/json'
                        }

                        response = requests.request("POST", url, headers=headers, data=payload)
                        of = json.loads(response.text)


                        if response.status_code!=201:
                            frappe.throw("Error : " + str(of) + "<br>Kosten : " + str(round(sle.total_outgoing_value,2)))                       

                        #---------- memoriaal kostenplaats inboeken --------------------
                        klant_referentie = frappe.get_value('Quotation', {'name': m.offerte}, 'klant_referentie')
                        kostenplaats = frappe.get_value('Lead', {'configurator_id': klant_referentie}, 'snelstart_kostenplaats')

                        url = "https://b2bapi.snelstart.nl/v2/memoriaalboekingen"

                        payload = json.dumps({
                            "datum": sle.posting_date,
                            "boekstuk": sle.name,
                            "omschrijving": module_naam + " Ref: " + klant_referentie,
                            "memoriaalBoekingsRegels": [
                                {
                                "omschrijving": module_naam + " Ref: " + klant_referentie,
                                "grootboek": {
                                    "id": "d5b39263-4c49-40c3-8830-712283afe7b4"
                                },
                                "kostenplaats": {
                                    "id": kostenplaats
                                },
                                "debet": sle.total_outgoing_value,
                                "credit": 0.0
                                },
                            ],
                            "dagboek": {
                                "id": "20bebb15-edf9-4b99-b960-95eae9bd509b"
                            }
                        })
                        headers = {
                        'Authorization': 'Bearer ' + token,
                        'Ocp-Apim-Subscription-Key': '9f637ff672984cb69298211844d36069',
                        'Content-Type': 'application/json'
                        }

                        response = requests.request("POST", url, headers=headers, data=payload)
                        of = json.loads(response.text)


                        if response.status_code!=201:
                            frappe.throw("Error : " + str(of) + "<br>Kosten : " + str(round(sle.total_outgoing_value,2)))   

                        comment += "- Voorraad Entry voor : " + m.module + " Aantal : " + str(m.qty) + "<br>"
                    else:
                        comment += "- Geen BOM voor : " + m.module + " Aantal : " + str(m.qty) + " gevonden!!<br>"
            
            delete_none = frappe.db.sql("""DELETE from `tabProductie Module` where parent = %(name)s and qty <= 0""", {"name": self.name}, as_dict=1)
            self.add_comment('Edit', comment)
        
        except Exception as e: 
            frappe.throw(str(e))

    def get_modules(self):
        self.set("productie_module", [])
        modules = frappe.db.sql(
            """ select
                    q.parent as quotation,
                    q.name as quotation_item,
                    qt.customer_name as klant,
                    q.item_code as item_code,
                    b.name as bom,
                    CONCAT("<a href='/desk#Form/Item/",q.item_code,"' target='_blank'>",IF(q.variant_code IS NOT NULL,CONCAT(q.item_name," (", q.variant_code,") "),q.item_name),"</a>") as item_name,
                    q.qty as besteld,
                    SUM(IFNULL(p.qty,0)) as klaar

                from `tabQuotation` qt, `tabQuotation Item` q
                    LEFT JOIN `tabProductie Module` p ON p.quotation_item = q.name and p.docstatus = 1, `tabBOM` b

                where 
                  qt.docstatus = 1 
                  and qt.name = q.parent 
                  and qt.vj_status = "In Productie"
                  and q.item_group IN ("Modules","Accessoires","Basis")
                  and q.item_code = b.item
                  and b.docstatus = 1
                  and b.is_default = 1
                  and b.is_active = 1

                group by q.name
                order by DATE_ADD(qt.transaction_date, INTERVAL qt.levertijd MONTH), qt.customer_name, q.idx, q.item_code asc""", as_dict=1)

        for data in modules:
            if data.klaar < data.besteld:
                self.append('productie_module', {
                    'offerte': data.quotation,
                    'quotation_item': data.quotation_item,
                    'klant': data.klant,
                    'item_code': data.item_code,
                    'module': data.item_name,
                    'besteld': data.besteld,
                    'klaar': data.klaar,
                    'bom': data.bom
                })

    def check_voorraad(self):
        try:
            for d in self.productie_module:
                available_qty = frappe.db.sql("""SELECT
                    bom_item.item_code,
                    bom_item.item_name ,
                    bom_item.stock_qty,
                    bom_item.stock_qty * {qty_to_produce},
                    max(b.actual_qty) as actual_qty,
                    IFNULL(max(FLOOR(b.actual_qty / (bom_item.stock_qty * {qty_to_produce}))),0) as voorraad
                FROM
                    `tabQuotation` q, `tabItem` AS i, `tabBOM Explosion Item` AS bom_item
                    LEFT JOIN `tabBin` b ON b.item_code = bom_item.item_code and b.actual_qty > 0

                WHERE
                    bom_item.parent = '{bom}' and bom_item.parenttype='BOM'
                    and i.name = bom_item.item_code
                    and i.bakje_bakje != 1
                    and q.name = "{offerte}"
                    and i.has_batch_no != 1
                    and i.sub_assembly_voorraad != 1

                GROUP BY bom_item.item_code ORDER BY bom_item.idx asc""".format(
                    qty_to_produce=(d.besteld-d.klaar),
                    qty_produced=d.qty,
                    item=d.item_code,
                    bom=d.bom,
                    offerte=d.offerte), as_dict=1)

                available_assembly_qty = frappe.db.sql("""SELECT
                    bom_item.item_code,
                    bom_item.item_name,
                    bom_item.qty,
                    bom_item.qty * {qty_to_produce},
                    max(b.actual_qty) as actual_qty,
                    max(FLOOR(b.actual_qty / (bom_item.qty * {qty_to_produce}))) as voorraad
                FROM
                    `tabQuotation` q, `tabItem` AS i, `tabBOM Item` AS bom_item
                    LEFT JOIN `tabBin` b ON b.item_code = bom_item.item_code and b.actual_qty > 0

                WHERE
                    bom_item.parent = '{bom}' and bom_item.parenttype='BOM'
                    and i.name = bom_item.item_code
                    and i.bakje_bakje != 1
                    and i.sub_assembly_voorraad = 1
                    and q.name = "{offerte}"
                    and i.has_batch_no != 1

                GROUP BY bom_item.item_code ORDER BY bom_item.idx asc""".format(
                    qty_to_produce=(d.besteld-d.klaar),
                    qty_produced=d.qty,
                    item=d.item_code,
                    bom=d.bom,
                    offerte=d.offerte), as_dict=1)

                available_batch_qty = frappe.db.sql("""SELECT
                        bom_item.item_code,
                        bom_item.item_name ,
                        bom_item.stock_qty,
                        bom_item.stock_qty * {qty_to_produce},
                        IFNULL(ledger.actual_qty,0) as actual_qty,
                        IFNULL(ledger.actual_qty,0) / (bom_item.stock_qty * {qty_to_produce}) as voorraad
                    FROM
                        `tabQuotation` q, `tabItem` AS i, `tabBOM Explosion Item` AS bom_item LEFT JOIN 
                        
                        (SELECT 
                            SUM(l.actual_qty) as actual_qty,
                            l.item_code,
                            l.batch_no
                        FROM `tabStock Ledger Entry` l, `tabQuotation` qt

                        WHERE
                        SUBSTRING_INDEX(l.batch_no, "-", 1) = qt.klant_referentie
                        and SUBSTRING_INDEX(l.batch_no, "-", -1) = qt.hpl_variant
                        and qt.name = "{offerte}"
                        
                        GROUP BY l.item_code) AS ledger ON bom_item.item_code = ledger.item_code

                    WHERE
                        bom_item.parent = '{bom}' and bom_item.parenttype='BOM' 
                        and i.name = bom_item.item_code
                        and i.bakje_bakje != 1
                        and q.name = "{offerte}"
                        and i.has_batch_no = 1


                GROUP BY bom_item.item_code ORDER BY bom_item.idx asc""".format(
                    qty_to_produce=(d.besteld-d.klaar),
                    qty_produced=d.qty,
                    item=d.item_code,
                    bom=d.bom,
                    offerte=d.offerte), as_dict=1)

                if d.verwerkt == 1:
                    d.status = '<span class="indicator green"><span class="hidden-xs">Verwerkt</span></span>'
                
                else:
                    if available_qty or available_assembly_qty or available_batch_qty:
                        if available_qty:
                            negative = 0
                            for i in available_qty:
                                if i.voorraad <= 0:
                                    negative += 1
                        if available_batch_qty:
                            for i in available_batch_qty:
                                if i.voorraad <= 0:
                                    negative += 1
                        if available_assembly_qty:
                            for i in available_assembly_qty:
                                if i.voorraad <= 0:
                                    negative += 1
                            
                        if negative > 0:
                            d.status = """
                            <span class="indicator red"><span class="hidden-xs">Tekort</span></span>
                            """
                        else:
                            d.status = """
                            <span class="indicator green"><span class="hidden-xs">Okay</span></span>
                            """
                    else:
                            d.status = """
                            <span class="indicator red"><span class="hidden-xs">No BOM</span></span>
                            """
        except Exception as e:
            frappe.throw(str(e) + '\nLine : ' + str(e.__traceback__.tb_lineno))
