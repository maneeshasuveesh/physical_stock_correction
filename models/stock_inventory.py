from odoo import api, fields, models, _


class StockInventoryInherited(models.Model):
    _inherit = 'stock.inventory'

    correction_id = fields.Many2one('stock.correction')