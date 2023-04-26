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
from frappe.utils import get_url, cstr, cint, flt, comma_or, getdate, nowdate, formatdate, format_time, now, add_to_date, now_datetime

class VoorraadTransactie(Document):

    def before_submit(self):
        if self.aantal <= self.actual_qty:
            if self.transactie_type=="Uit":
                self.snelstart_koppeling()
        else:
            frappe.throw("Uitgeboekte aantal mag niet meer dan voorraad aantal zijn!")


    def validate(self):
        if self.aantal > self.actual_qty:
            frappe.throw("Uitgeboekte aantal mag niet meer dan voorraad aantal zijn!")

    def snelstart_koppeling(self):

        value = frappe.get_value('Bin', {"item_code": self.artikel, "warehouse": self.locatie}, "valuation_rate")
        
        #--------------------create snelstart memoriaal-----------------------
        url = "https://auth.snelstart.nl/b2b/token"

        payload='grant_type=clientkey&clientkey=V0FobjJWLzUxQ0U4dnRrbk5DNjZyV3crUm1oZEUxclV3U3R0SVJKT0IyVE5mdURvaXFidmZKbS9NdkhPUlBjcTRiYkNDK2tMczFSZzNiUm9vcHQ5RWR4NDRWZU1ZSTE0M29zTnBVLzkrQktwM1ExSmhkOWs3RjUzL2pQNkFWY2pLUDhBMVI3K0pQRkNTRUJtNVBLMGsxeUxHd0hyazh5djhHRnl1dG85ZWxDSXFRdUJUbEpyM29UelVWZElPaXlkR3NtL3BITisxRzg3VGpxdnovYW5xcjFnak1ENUd0NkpLYkFwSVRrQnUyUHUzZ1FaTUhwK2tzVk1hSTE3dW4wRTp4WjJkWGl2amJzcTFjT3FPd0ZMRDkvOEVWcHE3VklwbXIxU0pmRVVTQWJiTWU2QkV3NHJyN3djNzRqaXBUM1lPdzJ2WGVpa1FGRmtGR0RuQ0lhMzVDZzNidnVVMjhBc2dvd3lYTDdGSk85cE12bTRsYm8vUzVYTkU0c3RiNXh0YzhKQ3ZpQnM1NzZmR2JNOHpjYWVvYm9oVzF1MlRWMm9WdVViZzZ6RndhVjN1Uk1iRjZNei9INnJuQTJnTEoxY0tYeGpTUFV4eU5sa2J4Vmh5OVovV25PSmFCcFZsL3FnVzVjYmVESTE5WVBUZVJJRFY4dUlpcFQ5eGFlWDhac0d1'
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        snelstart = json.loads(response.text)
        token = snelstart["access_token"]

        #---------- memoriaal credit voorraad uitboeken --------------------

        url = "https://b2bapi.snelstart.nl/v2/memoriaalboekingen"

        payload = json.dumps({
            "datum": nowdate(),
            "boekstuk": self.name,
            "omschrijving": self.artikel + "  : " + self.artikel_naam,
            "memoriaalBoekingsRegels": [
                {
                "omschrijving": self.artikel + "  : " + self.artikel_naam,
                "grootboek": {
                    "id": "fd7fb057-7d38-484b-9143-96f31eaae82b"
                },
                "debet": 0.0,
                "credit": round(self.aantal*float(value),2)
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
            frappe.throw("Error : " + str(of))


        #---------- memoriaal debet voorraad uitboeken --------------------

        url = "https://b2bapi.snelstart.nl/v2/memoriaalboekingen"

        payload = json.dumps({
            "datum": nowdate(),
            "boekstuk": self.name,
            "omschrijving": self.artikel + "  : " + self.artikel_naam,
            "memoriaalBoekingsRegels": [
                {
                "omschrijving": self.artikel + "  : " + self.artikel_naam,
                "grootboek": {
                    "id": "d5b39263-4c49-40c3-8830-712283afe7b4"
                },
                "debet": round(self.aantal*float(value),2),
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
            frappe.throw("Error : " + str(of))
        else:
            frappe.msgprint("Artikel uitgeboekt en in Snelstart ingevoerd!")