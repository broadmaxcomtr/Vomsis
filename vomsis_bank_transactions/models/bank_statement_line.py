from odoo import models, fields

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    vomsis_id = fields.Char(
        string='Vomsis ID',
        readonly=True,
        copy=False,
    )

    _sql_constraints = [
        ('unique_vomsis_id', 'unique(vomsis_id)', 'There is already a record with this Vomsis ID!'),
    ]