{
    'name': 'Vomsis Bank Transactions',
    'version': '1.0.0',
    'summary': 'Vomsis Bank Transactions',
    'description': """
      Create your bank transactions automatically with vomsis. Send payments from Odoo.
    """,
    'author': 'Broadmax',
    'website':'broadmax.com.tr',
    'license': 'LGPL-3',
    'category': 'Bank',
    'depends': ['account','account_accountant'],
    'data': [
        'data/ir_config_parameter_data.xml',
        'data/ir_cron.xml',
        'views/vomsis_service.xml',
        'views/account_journal.xml',
        'security/ir.model.access.csv',
        'wizard/account_journal_account_transaction_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
