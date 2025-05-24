from odoo import models, fields, api

class VomsisAccount(models.Model):
    _name = 'vomsis.account'
    _description = 'Vomsis API Accounts'
    _rec_name = 'name'

    service_id = fields.Many2one(
        'vomsis.service',
        string='Vomsis Service',
        required=True,
        ondelete='cascade',
    )
    vomsis_id = fields.Char(string='Vomsis ID',    readonly=True, store=True)
    bank_id = fields.Char(string='Bank ID', required=True, store=True)
    fec_name = fields.Char(string='Fec Name', required=True, store=True)
    account_number = fields.Char(string='Account Number', required=True, store=True)
    iban = fields.Char(string="IBAN", store=True)
    bank_name = fields.Char(string='Bank Name', readonly=True, store=True)
    bank_title = fields.Char(string='Bank Title', readonly=True, store=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]",
    )
    active = fields.Boolean(string='Active', default=True)

    name = fields.Char(string='Name', compute='_compute_name', store=True)

    @api.depends('iban', 'bank_title')
    def _compute_name(self):
        for rec in self:
            iban = rec.iban or ''
            title = rec.bank_title or ''
            fec = rec.fec_name or ''
            rec.name = f"{iban} – {title} - {fec}" if iban or title else ''