# -*- coding: utf-8 -*-
{
    'name': "Taiwan SmilePay Provider",
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 355,
    'summary': "台灣速買配金流，支援銀行轉帳、超商繳費",
    'description': """
    台灣速買配 第三方金流模組，支援 (ATM銀行轉帳/7-11 ibon/FamilyMart FamiPort)
    """,
    'author': "Sun Digital Dev LLC.",
    'website': "https://www.sundigit.net",
    'depends': ['payment'],
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_templates.xml',
        'views/payment_transaction_views.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_smilepay/static/src/js/**/*',
        ],
    },
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}