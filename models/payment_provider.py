# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('smilepay', 'SmilePay (速買配)')],
        ondelete={'smilepay': 'set default'}
    )
    
    smilepay_rvg2c = fields.Char(
        string="參數碼",
        required_if_provider='smilepay',
        help="SmilePay 提供的參數碼"
    )
    smilepay_dcvc = fields.Char(
        string="商家代號",
        required_if_provider='smilepay',
        help="SmilePay 提供的商家代號"
    )
    smilepay_verify_key = fields.Char(
        string="檢查碼",
        required_if_provider='smilepay',
        help="SmilePay 提供的檢查碼"
    )
    smilepay_smseid = fields.Char(
        string="商家驗證參數",
        required_if_provider='smilepay',
        size=4,
        help="SmilePay 提供的四位數商家驗證參數"
    )

    def _compute_feature_support_fields(self):
        """ Override of payment to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'smilepay').update({
            'support_tokenization': False,
            'support_express_checkout': False,
            'support_refund': 'none',
        })

    def _get_default_payment_method_codes(self):
        """ Override of payment to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'smilepay':
            return default_codes
        return [
            'smilepay_atm', 
            'smilepay_barcode', 
            'smilepay_ibon', 
            'smilepay_famiport'
        ]

    def _smilepay_calculate_mid_smilepay(self, smseid, amount, callback_smseid):
        """計算 Mid_smilepay 驗證碼"""
        a = smseid.zfill(4)
        b = str(int(amount)).zfill(8)
        c = callback_smseid[-4:]
        c = ''.join('9' if not x.isdigit() else x for x in c)
        d = a + b + c
        
        e = 0
        for i in range(1, len(d), 2):
            e += int(d[i])
        e *= 3

        f = 0
        for i in range(0, len(d), 2):
            f += int(d[i])
        f *= 9

        return e + f
    