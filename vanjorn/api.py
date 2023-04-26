# Copyright (c) 2021, IT2SME Co., Ltd.
# MIT License. See license.txt

from __future__ import unicode_literals

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

@frappe.whitelist(allow_guest=True)
def test_offerte():
    data = json.loads(frappe.local.form_dict.data)
    api_key = data['root'][0]['api_key']

    lead = frappe.get_value('Lead', {'configurator_id': data['root'][0]['configurator_id']}, 'name')
        
    return lead

@frappe.whitelist(allow_guest=True)
def offerte():
    try:
        data = json.loads(frappe.local.form_dict.data)
        api_key = data['root'][0]['api_key']

        offerte_datum = data['root'][0]['offerte_datum'].split('T')[0]
        customer_details = data['root'][0]['adres_klant'] + '<br>' + data['root'][0]['postcode']+ ' ' + data['root'][0]['plaats']

        items = []
        bpm = 0
        for b in data['root'][0]['artikelen']['artikelen']:
            if b['artikelen']['artikel_code'] == 201:
                bpm = b['artikelen']['artikel_prijs']

        for d in data['root'][0]['artikelen']['artikelen']:
            config_item = frappe.get_value('Item', {'configurator_id': d['artikelen']['artikel_code']}, 'name')
            i = frappe.db.get_value( 'Item', config_item, ['name','stock_uom','warehouse','item_group'], as_dict=1)
            
            if i:
                item_code = config_item
                uom = i.stock_uom
                warehouse = i.warehouse
                item_group = i.item_group
                
                if i.item_group == "Bus":
                    bus_bpm = bpm
                else:
                    bus_bpm = 0

            else:
                item_code = 'CU00003'
                uom = 'Stuks'
                warehouse = 'Suikerlaan - VJ'
                bus_bpm = 0
                item_group = "Custom"
            
            #----update item price-----
            item_price = frappe.get_value('Item Price', {'item_code': item_code}, 'name')

            if item_price:
                frappe.db.set_value("Item Price", item_price, 'price_list_rate', d['artikelen']['artikel_prijs'])

            else:
                doc = frappe.get_doc({
                    "doctype": "Item Price",
                    "buying": 0,
                    "currency": "EUR",
                    "idx": 0,
                    "item_code": item_code,
                    "lead_time_days": 0,
                    "packing_unit": 0,
                    "price_list": "Verkoop",
                    "price_list_rate": d['artikelen']['artikel_prijs'],
                    "selling": 1
                })
                doc.insert(ignore_permissions=True)
                frappe.db.commit()

            artikelen = {
                'sequence': d['artikelen']['sequence'],
                'item_code': item_code,
                'item_name': d['artikelen']['artikel_naam'],
                'description': d['artikelen']['helptext'],
                'variant_code': d['artikelen']['variant_code'],
                'variant_naam': d['artikelen']['variant_naam'],
                'qty': d['artikelen']['aantal'],
                'stock_qty': d['artikelen']['aantal'],
                'uom': uom,
                'conversion_factor': 1,
                'stock_uom': uom,
                'image': d['artikelen']['afbeelding_link'],
                'item_group': item_group,
                'rate': d['artikelen']['artikel_prijs'],
                'amount': d['artikelen']['aantal'] * d['artikelen']['artikel_prijs'],
                'base_rate': d['artikelen']['artikel_prijs'],
                'base_amount': d['artikelen']['aantal'] * d['artikelen']['artikel_prijs'],
                'warehouse': warehouse,
                'bpm': bus_bpm
            }
        
            items.append(artikelen)

    # --------------------------------------- insert log ------------------------------
        doc = frappe.get_doc({
                'doctype': 'Offerte Test',
                'api_data': str(data)
            })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        lead = frappe.get_value('Lead', {'configurator_id': data['root'][0]['configurator_id']}, 'name')

        if not lead:
        # --------------------------------------- insert lead ------------------------------
            doc = frappe.get_doc({
                    'doctype': 'Lead',
                    'lead_name': data['root'][0]['klant'],
                    'configurator_id': data['root'][0]['configurator_id'],
                    'email_id': data['root'][0]['contact_email'],
                    'transaction_date': offerte_datum,
                    'status': 'Quotation',
                    'source': 'Configurator',
                    'customer_details': customer_details,
                    'mobile_no': data['root'][0]['contact_telefoon'],
                    'website': data['root'][0]['configurator_link']

                })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            lead = frappe.get_value('Lead', {'configurator_id': data['root'][0]['configurator_id']}, 'name')

    # --------------------------------------- insert quotation ------------------------------
        doc = frappe.get_doc({
                'doctype': 'Quotation',
                'quotation_to': 'Lead',
                'customer_name': data['root'][0]['klant'],
                'lead': lead,
                'get_lead': lead,
                'party_name': lead,
                'transaction_date': offerte_datum,
                'remark': 'Offerte aangemaakt via configurator ID : ' + str(data['root'][0]['configurator_id']),
                'klant_referentie': data['root'][0]['configurator_id'],
                'status': 'Draft',
                'lead_source': 'Configurator',
                'configurator_link': data['root'][0]['configurator_link'],
                'screen_dump_link_1': data['root'][0]['screen_dump_link_1'],
                'screen_dump_link_2': data['root'][0]['screen_dump_link_2'],
                'address_display': customer_details,
                'contact_mobile': data['root'][0]['contact_telefoon'],
                'contact_email': data['root'][0]['contact_email'],
                'mobile_no': data['root'][0]['contact_telefoon'],
                'currency': 'EUR',
                'selling_price_list': 'Verkoop',
                'basis_bedrag': data['root'][0]['basis_bedrag'],
                'interieur_bedrag': data['root'][0]['interieur_bedrag'],
                'styling_bedrag': data['root'][0]['styling_bedrag'],
                'accessoires_bedrag': data['root'][0]['accessoires_bedrag'],
                'taxes_and_charges': 'VerkopenHoog',
                'payment_terms_template': 'Betaling in 2 termijnen',
                'items': items,
                'taxes': [{
                    'charge_type': 'On Net Total',
                    'account_head': '1630 - BTW Af te dragen Hoog - VJ',
                    'cost_center': 'Hoofd - VJ',
                    'rate': 21,
                    'included_in_print_rate': 1,
                    'description': 'BTW 21%'
                }]
            })
        doc.insert(ignore_permissions=True,ignore_links=True)
        frappe.db.commit()
        
        return  {"status": 100, "description": "Kostenplaats succesvol aangemaakt in SnelStart!" }
   
    except Exception as e:
       
        return  {"status": 900, "description": str(e) + '\nLine : ' + str(e.__traceback__.tb_lineno) }

@frappe.whitelist(allow_guest=True)
def kostenplaatsen(klant_referentie,customer_name):
    
    try:

        url = "https://auth.snelstart.nl/b2b/token"

        payload='grant_type=clientkey&clientkey=NzJ2d0RqSzVFcnZ4NkVwOTZMUU9QYUNJVGgwcGMvdEJUMWtjeFMyVUtXUlV1SWYyOXVyQnluYlNWdmxlRC9tTlJjazFhV1dBWXVLMUpzT3Evd1dDR3AyTU5BNW5vTXZmdFpCNTJIVmUwRjYyelFGNGxBZlk1M0cvVEMrL1FzK0lkK1FhbTVDRHVJaE4zOXFCL2ZrMldpVTlUTGtFTCt5RkNaNEVaRDFFOWNqQnloeGVpNjFYY0JpcmNOVEVIV1djNlkxdU82Rk5oUCt5TVh1eFJjNktOOGNyS2tTdU9KdUtpZzQ0dG5rSWM0dDhyazE5MlpnTWtFekt1d201SG9ZaDpvSE1ickZnRmZTUC9Bd2xYNGhNVzdOcTV0Q0kvYWhGck5UV2FtdG1JRU5pcXBMSDhnK1dDUS9FLzNoankvNnhwQWhBZTBrUFpDTmxOYUhja0gzRUR5MGMzQ09Gb295VVpVUzJzS0hDQXlKWitEZXNadnF1MTNHb1Fwc1NrZklSZ1dhdldvU3dmUkc3eHVyem5MZW5oUVp1RjlnRHNtL05paEJUbGtZVUxna2xWSnNCejhMKzBWdWQyeXo3ZDd5VjFLM2pXbDJqYWNjam8rZlpLUzI2bG05SUtzYkZDNlNBQ0MzaFNRcnNNbDJ5YVhGcGF4a0E0Qk8vWXoxcHg5SThP'
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.request("POST", url, headers=headers, data=payload)


        snelstart = json.loads(response.text)
        token = snelstart["access_token"]

        url = "https://b2bapi.snelstart.nl/v2/relaties"

        #----------kostenplaats check--------------------

        kost_url = "https://b2bapi.snelstart.nl/v2/kostenplaatsen"
        kost_payload = ""
        kost_headers = {
            'Authorization': 'Bearer ' + token,
            'Ocp-Apim-Subscription-Key': '9f637ff672984cb69298211844d36069',
            'Content-Type': 'application/json'
        }

        kost_response = requests.request("GET", kost_url, headers=kost_headers, data=kost_payload)

        kostenplaats = json.loads(kost_response.text)
        
        kost_id = next((d for d in kostenplaats if d['nummer'] == int(klant_referentie)), None)


        if not kost_id:
            url = "https://b2bapi.snelstart.nl/v2/kostenplaatsen"

            payload = json.dumps({
                "omschrijving": customer_name,
                "nonactief": False,
                "nummer": klant_referentie
            })
            headers = {
                'Authorization': 'Bearer ' + token,
                'Ocp-Apim-Subscription-Key': '9f637ff672984cb69298211844d36069',
                'Content-Type': 'application/json'
            }

            r = requests.request("POST", url, headers=headers, data=payload)

            res = json.loads(r.text)

            lead = frappe.get_value('Lead', {"configurator_id": klant_referentie}, "name")
            kid = res['id']
            d = frappe.get_doc('Lead', lead)
            d.snelstart_kostenplaats = kid
            d.save(ignore_permissions=True)
            frappe.db.commit()
        

        else:

            lead = frappe.get_value('Lead', {"configurator_id": klant_referentie}, "name")
            kid = kost_id["id"]
            d = frappe.get_doc('Lead', lead)
            d.snelstart_kostenplaats = kost_id["id"]
            d.save(ignore_permissions=True)
            frappe.db.commit()
        
        return { "status": 100, "description": kid}

    except Exception as e:

        frappe.throw(str(e))

@frappe.whitelist(allow_guest=True)
def klant_relatie(klant_referentie):

    try:

        klant_naam, email, telefoon = frappe.get_value('Lead', {"configurator_id": klant_referentie}, ["lead_name","email_id","mobile_no"])

        url = "https://auth.snelstart.nl/b2b/token"

        payload='grant_type=clientkey&clientkey=NzJ2d0RqSzVFcnZ4NkVwOTZMUU9QYUNJVGgwcGMvdEJUMWtjeFMyVUtXUlV1SWYyOXVyQnluYlNWdmxlRC9tTlJjazFhV1dBWXVLMUpzT3Evd1dDR3AyTU5BNW5vTXZmdFpCNTJIVmUwRjYyelFGNGxBZlk1M0cvVEMrL1FzK0lkK1FhbTVDRHVJaE4zOXFCL2ZrMldpVTlUTGtFTCt5RkNaNEVaRDFFOWNqQnloeGVpNjFYY0JpcmNOVEVIV1djNlkxdU82Rk5oUCt5TVh1eFJjNktOOGNyS2tTdU9KdUtpZzQ0dG5rSWM0dDhyazE5MlpnTWtFekt1d201SG9ZaDpvSE1ickZnRmZTUC9Bd2xYNGhNVzdOcTV0Q0kvYWhGck5UV2FtdG1JRU5pcXBMSDhnK1dDUS9FLzNoankvNnhwQWhBZTBrUFpDTmxOYUhja0gzRUR5MGMzQ09Gb295VVpVUzJzS0hDQXlKWitEZXNadnF1MTNHb1Fwc1NrZklSZ1dhdldvU3dmUkc3eHVyem5MZW5oUVp1RjlnRHNtL05paEJUbGtZVUxna2xWSnNCejhMKzBWdWQyeXo3ZDd5VjFLM2pXbDJqYWNjam8rZlpLUzI2bG05SUtzYkZDNlNBQ0MzaFNRcnNNbDJ5YVhGcGF4a0E0Qk8vWXoxcHg5SThP'
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        snelstart = json.loads(response.text)
        token = snelstart["access_token"]

        #----------klant check--------------------

        url = "https://b2bapi.snelstart.nl/v2/relaties"
        klant_url = "https://b2bapi.snelstart.nl/v2/relaties?$filter=Relatiecode eq " + str(klant_referentie)
        klant_payload = ""
        klant_headers = {
            'Authorization': 'Bearer ' + token,
            'Ocp-Apim-Subscription-Key': '9f637ff672984cb69298211844d36069',
            'Content-Type': 'application/json'
        }

        klant_response = requests.request("GET", klant_url, headers=klant_headers, data=klant_payload)

        klant_relatie = json.loads(klant_response.text)

        if not klant_relatie:

            payload = json.dumps({
            "relatiesoort": [
                "Klant"
            ],
            "relatiecode": klant_referentie,
            "naam": klant_naam,
            "mobieleTelefoon": telefoon,
            "email": email
            })
            headers = {
            'Authorization': 'Bearer ' + token,
            'Ocp-Apim-Subscription-Key': '9f637ff672984cb69298211844d36069',
            'Content-Type': 'application/json'
            }

            response = requests.request("POST", url, headers=headers, data=payload)

            res = json.loads(response.text)
            kid = res['id']
            lead = frappe.get_value('Lead', {"configurator_id": klant_referentie}, "name")

            d = frappe.get_doc('Lead', lead)
            d.snelstart_relatie = res['id']
            d.save(ignore_permissions=True)
            frappe.db.commit()
        
        else:
            lead = frappe.get_value('Lead', {"configurator_id": klant_referentie}, "name")
            kid = klant_relatie[0]['id']
            d = frappe.get_doc('Lead', lead)
            d.snelstart_relatie = klant_relatie[0]['id']
            d.save(ignore_permissions=True)
            frappe.db.commit()

        return  {"status": 100, "description": kid}
    
    except Exception as e:

        frappe.throw(str(e))

@frappe.whitelist(allow_guest=True)
def offerte_verkoop_order(klant_referentie,transaction_date,transaction_name,net_total,taxes,grand_total,btwsoort):

    try:

        klant_naam, snelstart_relatie, snelstart_kostenplaats = frappe.get_value('Lead', {"configurator_id": klant_referentie}, ["lead_name","snelstart_relatie","snelstart_kostenplaats"])

        url = "https://auth.snelstart.nl/b2b/token"

        payload='grant_type=clientkey&clientkey=NzJ2d0RqSzVFcnZ4NkVwOTZMUU9QYUNJVGgwcGMvdEJUMWtjeFMyVUtXUlV1SWYyOXVyQnluYlNWdmxlRC9tTlJjazFhV1dBWXVLMUpzT3Evd1dDR3AyTU5BNW5vTXZmdFpCNTJIVmUwRjYyelFGNGxBZlk1M0cvVEMrL1FzK0lkK1FhbTVDRHVJaE4zOXFCL2ZrMldpVTlUTGtFTCt5RkNaNEVaRDFFOWNqQnloeGVpNjFYY0JpcmNOVEVIV1djNlkxdU82Rk5oUCt5TVh1eFJjNktOOGNyS2tTdU9KdUtpZzQ0dG5rSWM0dDhyazE5MlpnTWtFekt1d201SG9ZaDpvSE1ickZnRmZTUC9Bd2xYNGhNVzdOcTV0Q0kvYWhGck5UV2FtdG1JRU5pcXBMSDhnK1dDUS9FLzNoankvNnhwQWhBZTBrUFpDTmxOYUhja0gzRUR5MGMzQ09Gb295VVpVUzJzS0hDQXlKWitEZXNadnF1MTNHb1Fwc1NrZklSZ1dhdldvU3dmUkc3eHVyem5MZW5oUVp1RjlnRHNtL05paEJUbGtZVUxna2xWSnNCejhMKzBWdWQyeXo3ZDd5VjFLM2pXbDJqYWNjam8rZlpLUzI2bG05SUtzYkZDNlNBQ0MzaFNRcnNNbDJ5YVhGcGF4a0E0Qk8vWXoxcHg5SThP'
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        snelstart = json.loads(response.text)
        token = snelstart["access_token"]

        url = "https://b2bapi.snelstart.nl/v2/verkoopboekingen"

        if float(taxes) > 0:
            order_data = {
                    "factuurdatum": transaction_date,
                    "factuurnummer": transaction_name,
                    "betalingstermijn": 7,
                    "klant": {
                        "id": snelstart_relatie
                    },
                    "omschrijving": "https://erp.vanjorn.com/desk#Form/Quotation/" + transaction_name,
                    "factuurbedrag": round(float(grand_total)*0.3,2),
                    "boekingsregels": [
                        {
                        "omschrijving": klant_naam,
                        "grootboek": {
                            "id": "842594fa-911f-46d8-b555-ad6d4013c908"
                        },
                        "kostenplaats": {
                            "id": snelstart_kostenplaats
                        },
                        "bedrag": round(round(float(grand_total)*0.3,2)-round((float(grand_total)*0.3)*0.21,2),2)
                        },
                    ],
                    "btw": [
                        {
                            "btwSoort": btwsoort,
                            "btwBedrag": round((float(grand_total)*0.3)*0.21,2)
                        }
                    ]
                }
        else:
            order_data = {
                    "factuurdatum": transaction_date,
                    "factuurnummer": transaction_name,
                    "betalingstermijn": 7,
                    "klant": {
                        "id": snelstart_relatie
                    },
                    "omschrijving": "https://erp.vanjorn.com/desk#Form/Quotation/" + transaction_name,
                    "factuurbedrag": round(float(grand_total)*0.3,2),
                    "boekingsregels": [
                        {
                        "omschrijving": klant_naam,
                        "grootboek": {
                            "id": "842594fa-911f-46d8-b555-ad6d4013c908"
                        },
                        "kostenplaats": {
                            "id": snelstart_kostenplaats
                        },
                        "bedrag": round(float(grand_total)*0.3,2)
                        },
                    ]
                }

        payload = json.dumps(order_data)
        headers = {
        'Authorization': 'Bearer ' + token,
        'Ocp-Apim-Subscription-Key': '9f637ff672984cb69298211844d36069',
        'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        of = json.loads(response.text)

        if response.status_code==201:
            d = frappe.get_doc('Quotation', transaction_name)
            d.snelstart_koppeling = 1
            d.save(ignore_permissions=True)
            frappe.db.commit()
            return {"status": 100, "description": "Kostenplaats, Relatie en Factuur in Snelstart aangemaakt!" }

        elif of[0]["errorCode"] == "BOE-0039":

            return {"status": 900, "description": "Error : " + of[0]["errorCode"] + "<br>" + of[0]["message"] + "<br>Berekening : " + str(round(round(float(grand_total)*0.3,2)-round((float(grand_total)*0.3)*0.21,2),2)) + " + " + str(round((float(grand_total)*0.3)*0.21,2)) + " = " + str(round(float(grand_total)*0.3,2))}

        else:
            return {"status": 900, "description": "Error : " + of[0]["errorCode"] + "<br>" + of[0]["message"] }
    
    except Exception as e:

        frappe.throw(str(e))

@frappe.whitelist(allow_guest=True)
def eind_factuur(posting_date,factuur_id,klant_referentie,grand_total,btw,btwsoort):

    try:

        aanbetaling, btw_aanbetaling = frappe.get_value('Quotation', {"klant_referentie": klant_referentie, "snelstart_koppeling": 1}, ["ROUND(grand_total*0.3,2) AS grand_total", "ROUND(total_taxes_and_charges*0.3,2) AS taxes"])
        klant_naam, snelstart_relatie, snelstart_kostenplaats = frappe.get_value('Lead', {"configurator_id": klant_referentie}, ["lead_name","snelstart_relatie","snelstart_kostenplaats"])

        url = "https://auth.snelstart.nl/b2b/token"

        payload='grant_type=clientkey&clientkey=NzJ2d0RqSzVFcnZ4NkVwOTZMUU9QYUNJVGgwcGMvdEJUMWtjeFMyVUtXUlV1SWYyOXVyQnluYlNWdmxlRC9tTlJjazFhV1dBWXVLMUpzT3Evd1dDR3AyTU5BNW5vTXZmdFpCNTJIVmUwRjYyelFGNGxBZlk1M0cvVEMrL1FzK0lkK1FhbTVDRHVJaE4zOXFCL2ZrMldpVTlUTGtFTCt5RkNaNEVaRDFFOWNqQnloeGVpNjFYY0JpcmNOVEVIV1djNlkxdU82Rk5oUCt5TVh1eFJjNktOOGNyS2tTdU9KdUtpZzQ0dG5rSWM0dDhyazE5MlpnTWtFekt1d201SG9ZaDpvSE1ickZnRmZTUC9Bd2xYNGhNVzdOcTV0Q0kvYWhGck5UV2FtdG1JRU5pcXBMSDhnK1dDUS9FLzNoankvNnhwQWhBZTBrUFpDTmxOYUhja0gzRUR5MGMzQ09Gb295VVpVUzJzS0hDQXlKWitEZXNadnF1MTNHb1Fwc1NrZklSZ1dhdldvU3dmUkc3eHVyem5MZW5oUVp1RjlnRHNtL05paEJUbGtZVUxna2xWSnNCejhMKzBWdWQyeXo3ZDd5VjFLM2pXbDJqYWNjam8rZlpLUzI2bG05SUtzYkZDNlNBQ0MzaFNRcnNNbDJ5YVhGcGF4a0E0Qk8vWXoxcHg5SThP'
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        snelstart = json.loads(response.text)
        token = snelstart["access_token"]

        url = "https://b2bapi.snelstart.nl/v2/verkoopboekingen"

        if float(btw) > 0:
            order_data = {
                    "factuurdatum": posting_date,
                    "factuurnummer": factuur_id,
                    "betalingstermijn": 7,
                    "klant": {
                        "id": snelstart_relatie
                    },
                    "omschrijving": "https://erp.vanjorn.com/desk#Form/Sales Invoice/" + factuur_id,
                    "factuurbedrag": round(float(grand_total)-float(aanbetaling),2),
                    "boekingsregels": [
                        {
                        "omschrijving": klant_naam,
                        "grootboek": {
                            "id": "842594fa-911f-46d8-b555-ad6d4013c908"
                        },
                        "kostenplaats": {
                            "id": snelstart_kostenplaats
                        },
                        "bedrag": round(round(float(grand_total)-float(aanbetaling),2)-round(float(btw),2),2)
                        },
                    ],
                    "btw": [
                        {
                            "btwSoort": btwsoort,
                            "btwBedrag": round(float(btw),2)
                        }
                    ]
                }
        else:
            order_data = {
                    "factuurdatum": posting_date,
                    "factuurnummer": factuur_id,
                    "betalingstermijn": 7,
                    "klant": {
                        "id": snelstart_relatie
                    },
                    "omschrijving": "https://erp.vanjorn.com/desk#Form/Sales Invoice/" + factuur_id,
                    "factuurbedrag": round(float(grand_total)-float(aanbetaling),2),
                    "boekingsregels": [
                        {
                        "omschrijving": klant_naam,
                        "grootboek": {
                            "id": "842594fa-911f-46d8-b555-ad6d4013c908"
                        },
                        "kostenplaats": {
                            "id": snelstart_kostenplaats
                        },
                        "bedrag": round(float(grand_total)-float(aanbetaling),2)
                        },
                    ]
                }

        payload = json.dumps(order_data)
        headers = {
        'Authorization': 'Bearer ' + token,
        'Ocp-Apim-Subscription-Key': '9f637ff672984cb69298211844d36069',
        'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        of = json.loads(response.text)


        if response.status_code==201:
            return {"status": 100, "description": "Eind Factuur in Snelstart aangemaakt!" }

        elif of[0]["errorCode"] == "BOE-0039":

            return {"status": 900, "description": "Error : " + of[0]["errorCode"] + "<br>" + of[0]["message"] + "<br>Berekening : " + str(round(round(float(grand_total)-float(aanbetaling),2)-round(float(btw),2),2)) + " + " + str(round(float(btw),2)) + " = " + str(round(float(grand_total)-float(aanbetaling),2))}

        else:
            return {"status": 900, "description": "Error : " + of[0]["errorCode"] + "<br>" + of[0]["message"] }
    
    except Exception as e:

        return {"status": 900, "description": "Error : " + str(e) }

@frappe.whitelist(allow_guest=True)
def losse_factuur(posting_date,customer,factuur_id,grand_total,net_total,btw,btwsoort,omzet_grootboek):

    try:

        url = "https://auth.snelstart.nl/b2b/token"

        payload='grant_type=clientkey&clientkey=NzJ2d0RqSzVFcnZ4NkVwOTZMUU9QYUNJVGgwcGMvdEJUMWtjeFMyVUtXUlV1SWYyOXVyQnluYlNWdmxlRC9tTlJjazFhV1dBWXVLMUpzT3Evd1dDR3AyTU5BNW5vTXZmdFpCNTJIVmUwRjYyelFGNGxBZlk1M0cvVEMrL1FzK0lkK1FhbTVDRHVJaE4zOXFCL2ZrMldpVTlUTGtFTCt5RkNaNEVaRDFFOWNqQnloeGVpNjFYY0JpcmNOVEVIV1djNlkxdU82Rk5oUCt5TVh1eFJjNktOOGNyS2tTdU9KdUtpZzQ0dG5rSWM0dDhyazE5MlpnTWtFekt1d201SG9ZaDpvSE1ickZnRmZTUC9Bd2xYNGhNVzdOcTV0Q0kvYWhGck5UV2FtdG1JRU5pcXBMSDhnK1dDUS9FLzNoankvNnhwQWhBZTBrUFpDTmxOYUhja0gzRUR5MGMzQ09Gb295VVpVUzJzS0hDQXlKWitEZXNadnF1MTNHb1Fwc1NrZklSZ1dhdldvU3dmUkc3eHVyem5MZW5oUVp1RjlnRHNtL05paEJUbGtZVUxna2xWSnNCejhMKzBWdWQyeXo3ZDd5VjFLM2pXbDJqYWNjam8rZlpLUzI2bG05SUtzYkZDNlNBQ0MzaFNRcnNNbDJ5YVhGcGF4a0E0Qk8vWXoxcHg5SThP'
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        snelstart = json.loads(response.text)
        token = snelstart["access_token"]

        #----------klant check--------------------


        has_lead = frappe.get_value('Customer', {'name': customer}, 'lead_name')
        omzet_grootboek = frappe.get_value('Snelstart Grootboek', {'name': omzet_grootboek}, 'grootboek_code')
        
        if has_lead:
            snelstart_relatie = frappe.get_value('Lead', {"name": has_lead}, "snelstart_relatie")

            if snelstart_relatie:
                klant_relatie = snelstart_relatie
                d = frappe.get_doc('Customer', customer)
                d.snelstart_referentie = snelstart_relatie
                d.save(ignore_permissions=True)
                frappe.db.commit()
        else:
            klant_relatie = frappe.get_value('Customer', {'name': customer}, 'snelstart_referentie')

            if not klant_relatie:
                url = "https://b2bapi.snelstart.nl/v2/relaties"

                payload = json.dumps({
                "relatiesoort": [
                    "Klant"
                ],
                "relatiecode": factuur_id,
                "naam": customer
                })

                headers = {
                'Authorization': 'Bearer ' + token,
                'Ocp-Apim-Subscription-Key': '9f637ff672984cb69298211844d36069',
                'Content-Type': 'application/json'
                }

                response = requests.request("POST", url, headers=headers, data=payload)

                res = json.loads(response.text)
                if response.status_code==201:
                    klant_relatie = res['id']

                    d = frappe.get_doc('Customer', customer)
                    d.snelstart_referentie = res['id']
                    d.save(ignore_permissions=True)
                    frappe.db.commit()

                else:
                
                    return {"status": 900, "description": str(response.text) }

            
        #---------- losse factuur --------------------

        url = "https://b2bapi.snelstart.nl/v2/verkoopboekingen"

        order_data = {
                "factuurdatum": posting_date,
                "factuurnummer": factuur_id,
                "betalingstermijn": 7,
                "klant": {
                    "id": klant_relatie
                },
                "omschrijving": "https://erp.vanjorn.com/desk#Form/Sales Invoice/" + factuur_id,
                "factuurbedrag": round(float(grand_total),2),
                "boekingsregels": [
                    {
                    "omschrijving": customer,
                    "grootboek": {
                        "id": omzet_grootboek
                    },
                    "bedrag": round(float(net_total),2)
                    },
                ],
                "btw": [
                    {
                        "btwSoort": btwsoort,
                        "btwBedrag": round(float(btw),2)
                    }
                ]
            }

        payload = json.dumps(order_data)
        headers = {
            'Authorization': 'Bearer ' + token,
            'Ocp-Apim-Subscription-Key': '9f637ff672984cb69298211844d36069',
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        of = json.loads(response.text)


        if response.status_code==201:
            return {"status": 100, "description": "Losse Factuur in Snelstart aangemaakt!" + "<br>Berekening : " + str(round(float(net_total),2)) + " + " + str(round(float(btw),2)) + " = " + str(round(float(grand_total),2)) }

        elif of[0]["errorCode"] == "BOE-0039":

            return {"status": 900, "description": "Error : " + of[0]["errorCode"] + "<br>" + of[0]["message"] + "<br>Berekening : " + str(round(float(net_total),2)) + " + " + str(round(float(btw),2)) + " = " + str(round(float(grand_total),2)) }

        else:
            return {"status": 900, "description": "Error : " + of[0]["errorCode"] + "<br>" + of[0]["message"] }
    
    except Exception as e:

        return {"status": 900, "description": "Error : " + str(e) }

@frappe.whitelist(allow_guest=True)
def journaal(grand_total,posting_date,journaal,customer):

    try:

        lead = frappe.get_value('Customer', {'name': customer}, 'lead_name')
        klant_referentie = frappe.get_value('Lead', {'name': lead}, 'configurator_id')

        #--------------------create snelstart memoriaal-----------------------
        url = "https://auth.snelstart.nl/b2b/token"

        payload='grant_type=clientkey&clientkey=NzJ2d0RqSzVFcnZ4NkVwOTZMUU9QYUNJVGgwcGMvdEJUMWtjeFMyVUtXUlV1SWYyOXVyQnluYlNWdmxlRC9tTlJjazFhV1dBWXVLMUpzT3Evd1dDR3AyTU5BNW5vTXZmdFpCNTJIVmUwRjYyelFGNGxBZlk1M0cvVEMrL1FzK0lkK1FhbTVDRHVJaE4zOXFCL2ZrMldpVTlUTGtFTCt5RkNaNEVaRDFFOWNqQnloeGVpNjFYY0JpcmNOVEVIV1djNlkxdU82Rk5oUCt5TVh1eFJjNktOOGNyS2tTdU9KdUtpZzQ0dG5rSWM0dDhyazE5MlpnTWtFekt1d201SG9ZaDpvSE1ickZnRmZTUC9Bd2xYNGhNVzdOcTV0Q0kvYWhGck5UV2FtdG1JRU5pcXBMSDhnK1dDUS9FLzNoankvNnhwQWhBZTBrUFpDTmxOYUhja0gzRUR5MGMzQ09Gb295VVpVUzJzS0hDQXlKWitEZXNadnF1MTNHb1Fwc1NrZklSZ1dhdldvU3dmUkc3eHVyem5MZW5oUVp1RjlnRHNtL05paEJUbGtZVUxna2xWSnNCejhMKzBWdWQyeXo3ZDd5VjFLM2pXbDJqYWNjam8rZlpLUzI2bG05SUtzYkZDNlNBQ0MzaFNRcnNNbDJ5YVhGcGF4a0E0Qk8vWXoxcHg5SThP'
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        snelstart = json.loads(response.text)
        token = snelstart["access_token"]

        #---------- memoriaal debit --------------------
        url = "https://b2bapi.snelstart.nl/v2/memoriaalboekingen"

        payload = json.dumps({
            "datum": posting_date,
            "boekstuk": journaal,
            "omschrijving": customer + " Ref: " + klant_referentie,
            "memoriaalBoekingsRegels": [
                {
                "omschrijving": customer + " Ref: " + klant_referentie,
                "grootboek": {
                    "id": "291cbccc-8e06-4b1e-8e72-f9f6b06eb7d8"
                },
                "debet": grand_total,
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
            return {"status": 900, "description": str(of) }

        #---------- memoriaal credit --------------------
        url = "https://b2bapi.snelstart.nl/v2/memoriaalboekingen"

        payload = json.dumps({
            "datum": posting_date,
            "boekstuk": journaal,
            "omschrijving": customer + " Ref: " + klant_referentie,
            "memoriaalBoekingsRegels": [
                {
                "omschrijving": customer + " Ref: " + klant_referentie,
                "grootboek": {
                    "id": "842594fa-911f-46d8-b555-ad6d4013c908"
                },
                "debet": 0.0,
                "credit": grand_total
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
            return {"status": 900, "description": str(of) }

        else:

            return {"status": 100, "description": "Eindrekening in Snelstart aangemaakt!"}
    
    except Exception as e:

        return {"status": 900, "description": "Error : " + str(e) }