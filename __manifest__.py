# -*- coding: utf-8 -*-
{
    'name': "Taiwan SmilePay Provider",
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'depends': ['payment'],
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_templates.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
    ],

    'description': """
    台灣速買配 (SmilePay) 第三方金流模組，支援:
    - ATM銀行轉帳
    - 超商代碼繳費
    - 7-11 ibon
    - 全家 FamiPort
    """,
    'author': "Sun Digital Dev LLC.",
    'website': "https://www.sundigit.net",
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}