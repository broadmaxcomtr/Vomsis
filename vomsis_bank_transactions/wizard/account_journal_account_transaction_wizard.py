from datetime import datetime, time
from odoo import models, fields, _
from odoo.exceptions import UserError

class AccountJournalAccountTransactionWizard(models.TransientModel):
    _name = 'account.journal.account.transaction.wizard'
    _description = 'Account Transactions Wizard'

    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    vomsis_account_id = fields.Many2one('vomsis.account', string='Vomsis Account', readonly=True)
    begin_date = fields.Date(string='Begin Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    def action_import_vomsis_transaction(self):
        self.ensure_one()

        if (self.end_date - self.begin_date).days > 7:
            raise UserError(_('The date range cannot exceed 7 days. Please select a range of 7 days or fewer.'))

        start_dt = datetime.combine(self.begin_date, time.min)
        end_dt = datetime.combine(self.end_date, time(hour=23, minute=59, second=0))

        service = self.vomsis_account_id.service_id
        begin_str = start_dt.strftime('%d-%m-%Y %H:%M:%S')
        end_str = end_dt.strftime('%d-%m-%Y %H:%M:%S')
        try:
            response = service.get_account_transactions(
                account_id=self.vomsis_account_id.vomsis_id,
                begin_date=begin_str,
                end_date=end_str,
            )
            transactions = response.get('transactions', [])
        except Exception as e:
            raise UserError(_('Vomsis transactions fetch failed: %s') % e)

        self.journal_id._create_bank_statement_lines(transactions)

        return {'type': 'ir.actions.act_window_close'}