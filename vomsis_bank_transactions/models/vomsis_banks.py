from odoo import models, fields

class VomsisBank(models.Model):
    _name = 'vomsis.bank'
    _description = 'Vomsis API Banks'

    service_id = fields.Many2one(
        'vomsis.service',
        string='Vomsis Service',
        required=True,
        ondelete='cascade',
    )
    vomsis_id = fields.Char(
        string="Vomsis ID",
        store=True
    )
    bank_name = fields.Char(
        string='Bank Name',
        required=True,
        store=True
    )
    bank_title = fields.Char(
        string='Bank Tittle',
        store=True
    )
    order = fields.Char(
        string='Order',
        store=True
    )
    vomsis_created_date = fields.Char(
        string='Active',
        store=True
    )
