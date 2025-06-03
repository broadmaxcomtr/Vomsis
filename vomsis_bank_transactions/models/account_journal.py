from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    vomsis_account_ids = fields.One2many(
        'vomsis.account', 'journal_id',
        string='Vomsis Accounts',
    )
    vomsis_account_id = fields.Many2one(
        'vomsis.account',
        string='Vomsis Account',
        compute='_compute_vomsis_account_id',
        inverse='_inverse_vomsis_account_id',
        store=True,
        readonly=False,
        domain="[('active','=',True),('company_id','=',company_id)]",
    )

    @api.depends('vomsis_account_ids')
    def _compute_vomsis_account_id(self):
        for journal in self:
            journal.vomsis_account_id = journal.vomsis_account_ids[:1] or False

    def _inverse_vomsis_account_id(self):
        for journal in self:
            old = journal.vomsis_account_ids.filtered(
                lambda acc: acc != journal.vomsis_account_id
            )
            if old:
                old.write({'journal_id': False})
            if journal.vomsis_account_id:
                journal.vomsis_account_id.write({'journal_id': journal.id})

    def action_get_account_transaction(self):
        self.ensure_one()
        return {
            'name': 'Get Account Transactions',
            'type': 'ir.actions.act_window',
            'res_model': 'account.journal.account.transaction.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_journal_id': self.id,
                'default_vomsis_account_id': self.vomsis_account_id.id,
            },
        }
    
    def _create_bank_statement_lines(self, transactions):
        self.ensure_one()
        ids = [str(tx.get('id')) for tx in transactions]
        existing = set(self.env['account.bank.statement.line']
                    .search([('journal_id', '=', self.id), ('vomsis_id', 'in', ids)])
                    .mapped('vomsis_id'))
        for tx in transactions:
            tx_id = str(tx.get('id'))
            if tx_id in existing:
                continue 
            try:
                dt = datetime.strptime(tx.get('accounting_date', ''), '%Y-%m-%d %H:%M:%S')
            except Exception:
                dt = datetime.now()
            amount = float(tx.get('amount') or 0.0)
            self.env['account.bank.statement.line'].create({
                'journal_id': self.id,
                'vomsis_id': tx_id,
                'date': dt.date(),
                'payment_ref': tx.get('description'),
                'amount': amount,
            })
            _logger.info(tx)



    # def _cron_import_vomsis_transactions(self):
    #     cron = self.env.ref('vomsis_api.ir_cron_import_vomsis_transactions')
    #     if cron.lastcall:
    #         begin_dt = fields.Datetime.from_string(cron.lastcall)
    #     else:
    #         begin_dt = datetime.now() - timedelta(minutes=15)
    #     end_dt = fields.Datetime.now()
    #     begin_str = begin_dt.strftime('%d-%m-%Y %H:%M:%S')
    #     end_str = end_dt.strftime('%d-%m-%Y %H:%M:%S')
    #
    #     journals = self.search([
    #         ('type', '=', 'bank'),
    #         ('vomsis_account_id', '!=', False),
    #     ])
    #     for journal in journals:
    #         service = journal.vomsis_account_id.service_id
    #         try:
    #             res = service.get_account_transactions(
    #                 account_id=journal.vomsis_account_id.vomsis_id,
    #                 begin_date=begin_str,
    #                 end_date=end_str,
    #             )
    #             txs = res.get('transactions', [])
    #         except Exception as e:
    #             continue
    #         journal._create_bank_statement_lines(txs)
    #
    #     cron.write({'lastcall': fields.Datetime.to_string(end_dt)})
    #     return True
