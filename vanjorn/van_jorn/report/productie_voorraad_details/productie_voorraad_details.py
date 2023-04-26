# Copyright (c) 2013, IT2SME Co., Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()

	data = get_bom_stock(filters)

	return columns, data

def get_columns():
	"""return columns"""
	columns = [
		_("Item") + ":Link/Item:150",
		_("Description") + "::250",
		_("Qty per BOM Line") + ":Float:100",
		_("Required Qty") + ":Float:100",
		_("In Stock Qty") + ":Float:100",
		_("Enough Parts to Build") + ":Float:200",
	]

	return columns

def get_bom_stock(filters):
	conditions = ""
	bom = filters.get("quotation_bom").split("&")[1]
	quotation = filters.get("quotation_bom").split("&")[0]

	table = "`tabBOM Explosion Item`"
	qty_field = "stock_qty"

	qty_to_produce = filters.get("qty_to_produce", 1)
	if  int(qty_to_produce) <= 0:
		frappe.throw(_("Quantity to Produce can not be less than Zero"))

	if filters.get("show_exploded_view"):
		table = "`tabBOM Explosion Item`"
		qty_field = "stock_qty"

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value("Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
		if warehouse_details:
			conditions += " and exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and ledger.warehouse = wh.name)" % (warehouse_details.lft,
				warehouse_details.rgt)
		else:
			conditions += " and ledger.warehouse = '%s'" % frappe.db.escape(filters.get("warehouse"))

	else:
		conditions += ""

	return frappe.db.sql("""
			SELECT
				bom_item.item_code,
				bom_item.item_name,
				bom_item.{qty_field},
				bom_item.{qty_field} * {qty_to_produce},
				max(b.actual_qty) as actual_qty,
				max(FLOOR(b.actual_qty / (bom_item.{qty_field} * {qty_to_produce})))
			FROM
				`tabQuotation` q, `tabItem` AS i, {table} AS bom_item
				LEFT JOIN `tabBin` b ON b.item_code = bom_item.item_code and b.actual_qty > 0

			WHERE
				bom_item.parent = '{bom}' and bom_item.parenttype='BOM'
                and i.name = bom_item.item_code
                and i.bakje_bakje != 1
                and q.name = "{offerte}"
                and i.has_batch_no != 1

			GROUP BY bom_item.item_code

            UNION ALL
            
            SELECT
				bom_item.item_code,
				bom_item.item_name,
				bom_item.{qty_field},
				bom_item.{qty_field} * {qty_to_produce},
				max(b.actual_qty) as actual_qty,
				max(FLOOR(b.actual_qty / (bom_item.{qty_field} * {qty_to_produce})))
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

			GROUP BY bom_item.item_code

            UNION ALL

            SELECT
                bom_item.item_code,
                bom_item.item_name ,
                bom_item.stock_qty,
                bom_item.stock_qty * {qty_to_produce},
                IFNULL(ledger.actual_qty,0) as actual_qty,
                IFNULL(ledger.actual_qty,0) / (bom_item.stock_qty * {qty_to_produce})
            FROM
                `tabQuotation` q, `tabItem` AS i, {table} AS bom_item LEFT JOIN 
                
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
                


            GROUP BY bom_item.item_code
            
            ORDER BY 1 asc""".format(
				qty_field=qty_field,
				table=table,
				conditions=conditions,
				bom=bom,
                offerte=quotation,
				qty_to_produce=qty_to_produce or 1)
			)
