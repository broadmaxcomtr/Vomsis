from datetime import datetime
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class VomsisService(models.Model):
    _name = 'vomsis.service'
    _description = 'Vomsis API Service Configuration'

    name = fields.Char(string="Name", store=True)
    app_key = fields.Char(string='API Key', required=True)
    app_secret = fields.Char(string='API Secret', required=True, password=True)
    token = fields.Char(string='Access Token', copy=False, readonly=True)

    company_name = fields.Char(string="Company Name", readonly=True)
    company_title = fields.Char(string="Company Title", readonly=True)
    contact_name = fields.Char(string="Contact Name", readonly=True)
    email = fields.Char(string="Email", readonly=True)
    phone = fields.Char(string="Phone", readonly=True)
    code = fields.Char(string="Code", readonly=True)
    
    vomsis_banks = fields.One2many(
        comodel_name='vomsis.bank',
        inverse_name='service_id',
        string='Banks',
    )
    vomsis_accounts = fields.One2many(
        comodel_name='vomsis.account',
        inverse_name='service_id',
        string='Accounts',
    )
    last_date=fields.Date(string="Last Date")
    last_id=fields.Char(string="Last Id")

    @api.model
    def _get_root_url(self):
        param_obj = self.env['ir.config_parameter'].sudo()
        url = param_obj.get_param('vomsis.api')
        if not url:
            raise UserError(_(
                "Vomsis API URL is not configured. "
                "Please set the 'vomsis.api' system parameter."
            ))
        return url

    def authenticate(self):
        """Authenticate and store the raw token; expiration'ı 401 yakalayarak yenileyebiliriz."""
        self.ensure_one()
        url = f"{self._get_root_url()}/authenticate"
        payload = {
            'app_key': self.app_key,
            'app_secret': self.app_secret,
        }
        try:
            resp = requests.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise UserError(_('Vomsis authentication failed: %s') % e)

        if data.get('status') != 'success':
            raise UserError(_('Authentication başarısız.: %s') % data)

        token = data.get('token')
        if not token:
            raise UserError(_('Authentication was successful but the token was not obtained. Please try again.'))
        self.token = token
        self.fetch_license_info()

        return token

    def _get_headers(self):
        token = self.token or self.authenticate()
        return {'Authorization': f'Bearer {token}'}
    
    def request(self, method, endpoint, **kwargs):
        self.ensure_one()
        url = f"{self._get_root_url()}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        if 'headers' in kwargs:
            kwargs['headers'].update(headers)
        else:
            kwargs['headers'] = headers
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise UserError(_('Error during API request (%s %s): %s') % (method, endpoint, e))

    def get(self, endpoint, params=None):
        """Convenience method for GET requests"""
        return self.request('GET', endpoint, params=params)

    def post(self, endpoint, data=None, json=None):
        """Convenience method for POST requests"""
        return self.request('POST', endpoint, data=data, json=json)

    def delete(self, endpoint, params=None):
        """Convenience method for DELETE requests"""
        return self.request('DELETE',endpoint,params=params)

    def put(self, endpoint, data=None, json=None):
        """Convenience PUT"""
        return self.request('PUT', endpoint, data=data, json=json)

##########################################
    def get_licence_info(self):
        """Fetch All Licence datas"""
        return self.get('license_info')
    
    def fetch_license_info(self):
        self.ensure_one()
        data = self.get('license_info')
        if data.get('status') != 'success' or 'license' not in data:
            raise UserError(_('License info fetch failed: %s') % data)

        lic = data['license']
        self.write({
            'company_name':lic.get('company_name', ''),
            'company_title':lic.get('company_title', ''),
            'contact_name':lic.get('name', ''),
            'email':lic.get('email', ''),
            'phone':lic.get('phone', ''),
            'code':lic.get('code', ''),
        })
        return True
    
    def get_banks(self):
        """Fetch All Bank datas"""
        return self.get('banks')

    def fetch_banks(self):
        self.ensure_one()
        data = self.get('banks')
        if data.get('status') != 'success' or 'banks' not in data:
            raise UserError(_('Bank import failed: %s') % data)

        lines = [(5, 0, 0)]
        for bank in data['banks']:
            lines.append((0, 0, {
                'vomsis_id': str(bank.get('id', '')),
                'bank_name': bank.get('bank_name', ''),
                'bank_title': bank.get('bank_title', ''),
                'order': str(bank.get('order', '')),
                'vomsis_created_date': bank.get('created_at', ''),
            }))
        self.write({'vomsis_banks': lines})
        return True
    
    def get_accounts(self):
        """Fetch All Account datas"""
        return self.get('accounts')
    
    def fetch_accounts(self):
        self.ensure_one()
        data = self.get('accounts')
        if data.get('status') != 'success' or 'accounts' not in data:
            raise UserError(_('Failed to import accounts: %s') % data)

        existing_ids = self.vomsis_accounts.mapped('vomsis_id')
        new_lines = []
        for acct in data['accounts']:
            vid = str(acct.get('id', ''))
            if vid in existing_ids:
                continue
            bank = acct.get('bank') or {}
            new_lines.append((0, 0, {
                'vomsis_id':vid,
                'bank_id':str(acct.get('bank_id', '')),
                'fec_name':acct.get('fec_name', ''),
                'account_number':acct.get('account_number', ''),
                'iban':acct.get('iban', ''),
                'active':acct.get('status') == 1,
                'bank_name':bank.get('bank_name', ''),
                'bank_title':bank.get('bank_title', ''),
            }))
        if new_lines:
            self.write({'vomsis_accounts': new_lines})
        return True
    
    def get_bank_accounts(self, bank_id):
        """
        Fetch all accounts for a given bank.
        GET /api/v2/banks/{bank_id}/accounts
        """
        self.ensure_one()
        endpoint = f"banks/{bank_id}/accounts"
        return self.get(endpoint)

    def get_account_by_id(self,account_id):
        """
        Fetch account for given account_id
        GET /api/v2/accounts/{id}
        :param account_id:
        """
        self.ensure_one()
        endpoint = f"accounts/{account_id}"
        return self.get(endpoint)

    def get_account_transactions(self, account_id, begin_date=None, end_date=None, last_id=None, date_type=None,
                                 types=None):
        """
        Fetch transactions for an account with optional filters.
        GET /api/v2/accounts/{account_id}/transactions
        Required: beginDate and endDate or lastId
        Optional:
            lastId: only transactions after this ID
            dateType: 'system_date' or 'accounting_date'
            types: comma-separated list of transaction type codes, e.g. 'TRFGEL,DBSTAH'
        Date format: 'dd-MM-YYYY HH:mm:ss'
        """
        self.ensure_one()
        endpoint = f"accounts/{account_id}/transactions"
        params = {}
        if begin_date and end_date:
            params['beginDate'] = begin_date
            params['endDate'] = end_date
        if last_id is not None:
            params['lastId'] = last_id
        if date_type:
            params['dateType'] = date_type
        if types:
            params['types'] = types
        if not (params.get('beginDate') and params.get('endDate')) and 'lastId' not in params:
            raise UserError(_('You must provide either begin_date/end_date or last_id.'))
        return self.get(endpoint, params=params)

    def get_bank_transactions(self):
        """
        Fetch transactions.
        GET /api/v2/transactions
        Required: beginDate and endDate or lastId
        Date format: 'dd-MM-YYYY HH:mm:ss'
        """
        self.ensure_one()
        endpoint = "transactions"
        params = {}

        if self.last_id:
            params['lastId'] = self.last_id
        else:
            if not self.last_date:
                raise UserError(_('No last_date set and no last_id provided.'))
            params['beginDate'] = self.last_date.strftime('%d-%m-%Y %H:%M:%S')
            params['endDate'] = datetime.now().strftime('%d-%m-%Y %H:%M:%S')

        result = self.get(endpoint, params=params)

        tx_list = result.get('transactions') or []
        if tx_list:
            last_tx = tx_list[-1]
            self.last_id = last_tx.get('id')
            self.last_date = datetime.now()

        return result

    def import_transaction_lines(self):

        self.ensure_one()

        data = self.get_bank_transactions()
        tx_list = data.get('transactions') or []

        txs_by_journal = {}
        for tx in tx_list:
            v_acc_id = tx.get('account', {}).get('id')
            acct_cfg = self.vomsis_accounts.filtered(
                lambda a: a.account_number == f"{v_acc_id}"
            )
            if not acct_cfg:
                continue
            journal = acct_cfg.journal_id
            if not journal:
                continue

            txs_by_journal.setdefault(journal, []).append(tx)

        for journal, txs in txs_by_journal.items():
            journal._create_bank_statement_lines(txs)

        return tx_list

    def get_transaction_types(self):
        return self.get('transaction_types')

    def get_pos_report_stations(self):
        return self.get('pos-rapor/stations')

    def get_station_transactions(self, id, begin_date=None, end_date=None,  date_type=None):
        """
        Fetch transactions.
        GET /api/v2/transactions
        Required: beginDate and endDate or lastId
        Optional:
            lastId: only transactions after this ID
            dateType: 'system_date' or 'accounting_date'
            types: comma-separated list of transaction type codes, e.g. 'TRFGEL,DBSTAH'
        Date format: 'dd-MM-YYYY HH:mm:ss'
        """
        self.ensure_one()
        endpoint = f"pos-rapor/stations/{id}/transactions"
        params = {}
        if begin_date and end_date:
            params['beginDate'] = begin_date
            params['endDate'] = end_date
        if date_type:
            params['dateType'] = date_type
        if not (params.get('beginDate') and params.get('endDate')) and 'lastId' not in params:
            raise UserError(_('You must provide either begin_date/end_date or last_id.'))
        return self.get(endpoint, params=params)

    def create_transactions(self,data):
        """
        Create Transaction
        Example Data
        ```
        --data '{
                "key": "20210923154112945192",  //optional , unique
                "vms_transaction_type": "TRFGEL",
                "bank_account_id": 36,
                "system_date": "2023-06-08 10:55:00",
                "transaction_type": "eft",
                "description": "Vomsis Bilişim AŞ",
                "amount": "-1200.00",
                "current_balance": "23027.68",
                "resource_code": null,
                "opponent_title": "Vomsis Bilişim Teknolojileri A.Ş.",
                "opponent_iban": "TR810020300008028863000001",
                "opponent_taxno": "6340759273",
                "erp_processed" : true
            }'
        ```
        """
        return self.post('transactions/create',data)

    def update_transaction_move(self,data,move_id):
        """
        {
        "erp_processed" : true
        }
        :param data:
        :param move_id:
        :return:
        """
        endpoint=f"transactions/{move_id}/erp_status_update"
        return self.post(endpoint,data)

    def get_transactions_move(self, move_id, begin_date=None, end_date=None):

        self.ensure_one()
        endpoint = f"transactions/{move_id}"
        params = {}
        if begin_date and end_date:
            params['beginDate'] = begin_date
            params['endDate'] = end_date
        if not (params.get('beginDate') and params.get('endDate')) not in params:
            raise UserError(_('You must provide either begin_date/end_date.'))
        return self.get(endpoint, params=params)

    def delete_transactions_move(self,move_id):
        endpoint=f"transactions/{move_id}/delete"
        return self.delete(endpoint)


    @api.model
    def _cron_import_transaction_lines(self):

        valid_services = self.search([
            ('app_key', '!=', False),
            ('app_secret', '!=', False),
        ])
        for service in valid_services:
            try:
                service.import_transaction_lines()
            except Exception as e:
                raise UserError(_('App key and App secret must be set. %s')% e)

        return True