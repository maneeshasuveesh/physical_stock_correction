from odoo import api, fields, models, _
from odoo.exceptions import Warning


class StockCorrection(models.Model):
    _name = "stock.correction"
    _description = "Physical Stock Correction"

    @api.multi
    def compute_inv_adjustment_info(self):
        for correction in self:
            correction.inv_ids = self.env['stock.inventory'].search([('correction_id', '=', correction.id)])
            correction.inv_count = len(correction.inv_ids)

    name = fields.Char('Name', default="New")
    start_date = fields.Date('Correction Date', default=fields.Date.today)

    line_ids = fields.One2many('stock.correction.line', 'correction_id', 'Corrections')
    state = fields.Selection(
        [('draft', 'Draft'), ('to_recheck', 'To Recheck'), ('to_approve', 'To Approve'), ('done', 'Done'),
         ('rejected', 'Rejected'), ('send_back', 'Send Back')
         ], default='draft')
    inv_count = fields.Integer('Inv Adjustment Count', compute='compute_inv_adjustment_info')
    inv_ids = fields.Many2many('stock.inventory', 'Inventories', compute='compute_inv_adjustment_info')
    approved_date = fields.Date('Approved Date')

    # add sequence number when creating physical Stock correction
    @api.model
    def create(self, vals):
        vals.update({'name': self.env['ir.sequence'].next_by_code('stock.correction')})
        return super(StockCorrection, self).create(vals)

    @api.multi
    def action_send_to_recheck(self):
        if not self.line_ids:
            raise Warning('Please add correction lines!')
        else:
            self.state = 'to_recheck'

    @api.multi
    def action_recheck(self):
        actual_quantity = 0
        for line in self.line_ids:
            domain = [('location_id', '=', line.location_id.id)]
            if line.lot_id:
                domain.append(('lot_id', '=', line.lot_id.id))
            quants = self.env['stock.quant'].search(domain)
            if quants:
                actual_quantity = sum(quants.mapped('quantity'))
            line.actual_quantity = actual_quantity
            line.difference = line.actual_quantity - line.physical_quantity

    @api.multi
    def action_submit(self):
        # will not allow to submit without marking corrections ok or not
        if any(line.state == 'draft' for line in self.line_ids):
            raise Warning('Please verify the each corrections!')
        self.state = 'to_approve'

    @api.multi
    def action_approve(self):
        # if all of the lines are send back and still trying to approve from the main form send it to state send_back
        if all(line.state == 'send_back' for line in self.line_ids):
            self.state = 'send_back'
        # if all of the lines are rejected and still trying to approve from the main form send it to state rejected
        elif all(line.state == 'rejected' for line in self.line_ids):
            self.state = 'rejected'
        else:
            for line in self.line_ids:
                if line.state == 'verified':
                    inventory = self.env['stock.inventory'].create({
                        'name': 'Physical Stock Correction' + '-' + line.correction_id.name,
                        'filter': 'lot',
                        'lot_id': line.lot_id.id,
                        'correction_id': line.correction_id.id,
                        'line_ids': [(0, 0, {
                            'product_id': line.lot_id.product_id.id,
                            'product_qty': line.physical_quantity,
                            'location_id': line.location_id.id,
                            'prod_lot_id': line.lot_id.id

                        })]
                    })
                    inventory.action_start()
                    inventory.action_validate()

            self.state = 'done'
            self.approved_date = fields.Date.today()

    # View inventory adjustments created from the stock correction
    @api.multi
    def action_view_inv_adjustments(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.inventory",
            "domain": [("id", "in", self.inv_ids.ids)],
            'view_type': 'form',
            'view_mode': 'tree,form',
            "name": "Inventory Adjustments"

        }

    # reject all correction lines
    @api.multi
    def action_reject(self):
        if any(not line.remarks for line in self.line_ids):
            raise Warning('Please add remarks!')
        else:
            for line in self.line_ids:
                line.state = 'rejected'
            self.state = 'rejected'

    # send back all correction lines
    @api.multi
    def action_send_back(self):
        if any(not line.remarks for line in self.line_ids):
            raise Warning('Please add remarks!')
        else:
            for line in self.line_ids:
                line.state = 'send_back'
            self.state = 'send_back'


class StockCorrectionLine(models.Model):
    _name = "stock.correction.line"
    _description = "Physical Stock Correction Line"
    _rec_name = "correction_id"

    correction_id = fields.Many2one('stock.correction', 'Stock Correction')
    physical_quantity = fields.Float('Physical Quantity')
    lot_id = fields.Many2one('stock.production.lot', 'Batch', required=True)
    expiry_date = fields.Datetime('Expiry Date', related='lot_id.life_date')
    location_id = fields.Many2one('stock.location', 'Bin', required=True)
    actual_quantity = fields.Float('Actual Quantity')
    difference = fields.Float('Difference')
    state = fields.Selection(
        [('draft', 'Draft'), ('verified', 'Ok'), ('not_ok', 'Not Ok'), ('approved', 'Approved'),
         ('send_back', 'Send Back'),
         ('rejected', 'Rejected'), ('done', 'Done')
         ], default='draft')
    send_back_quantity = fields.Float('Send Back Quantity')
    remarks = fields.Text('Remarks')
    attachment_ids = fields.Many2many('ir.attachment', 'stock_correction_line_ir_attachments_rel',
                                      string="Attachments")

    @api.multi
    def action_verified(self):
        self.state = 'verified'

    @api.multi
    def action_not_ok(self):
        self.state = 'not_ok'

    @api.multi
    def action_approve(self):
        for line in self:
            if line.state == 'verified':
                inventory = self.env['stock.inventory'].create({
                    'name': 'Physical Stock Correction' + '-' + line.correction_id.name,
                    'filter': 'lot',
                    'lot_id': line.lot_id.id,
                    'correction_id': line.correction_id.id,
                    'line_ids': [(0, 0, {
                        'product_id': line.lot_id.product_id.id,
                        'product_qty': line.physical_quantity,
                        'location_id': line.location_id.id,
                        'prod_lot_id': line.lot_id.id

                    })]
                })
                inventory.action_start()
                inventory.action_validate()
                self.state = 'done'

    @api.multi
    def action_reject(self):
        if not self.remarks:
            raise Warning('Please add Remarks!')
        else:
            self.state = 'rejected'
            self.correction_id.state = 'rejected'

    @api.multi
    def action_send_back(self):
        if not self.remarks:
            raise Warning('Please add Remarks!')
        else:
            self.state = 'send_back'
