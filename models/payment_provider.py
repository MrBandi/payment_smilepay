import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('smilepay', 'SmilePay')],
        ondelete={'smilepay': 'set default'}
    )
    
    smilepay_merchant_id = fields.Char(
        string="商家代號 (Dcvc)",
        help="請至商家後台確認",
        required_if_provider='smilepay',
    )
    smilepay_parameter_code = fields.Char(
        string="參數碼 (Rvg2c)",
        help="請至商家後台確認",
        required_if_provider='smilepay',
    )
    smilepay_verify_key = fields.Char(
        string="檢查碼 (Verify_key)",
        help="請至商家後台確認",
        required_if_provider='smilepay',
    )
    smilepay_payment_method = fields.Selection(
        string="付款方式",
        selection=[
            ('vacc', 'ATM 銀行轉帳'),
            ('ibon', '7-11 ibon'),
            ('fami', '全家 FamiPort'),
        ],
        required_if_provider='smilepay',
        default='vacc',
        help="選擇預設的付款方式",
    )
    smilepay_environment = fields.Selection(
        string="環境",
        selection=[('test', '測試環境'), ('prod', '正式環境')],
        default='test',
        required_if_provider='smilepay',
    )
    
    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page for providers without credentials.
        """
        super()._compute_view_configuration_fields()
        for provider in self:
            if provider.code == 'smilepay':
                provider.show_credentials_page = True
                provider.show_pre_msg = True
                provider.show_done_msg = True
                provider.show_cancel_msg = True
    
    @api.model
    def _get_supported_currencies(self):
        """ Override of payment to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code != 'smilepay':
            return supported_currencies
        
        # 僅支援新台幣
        twd_currency = self.env.ref('base.TWD', raise_if_not_found=False)
        if twd_currency:
            return self.env['res.currency'].browse(twd_currency.id)
        return supported_currencies
    
    def _get_default_payment_method_codes(self):
        """ Override of payment to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'smilepay':
            return default_codes
        
        # 根據設定的付款方式映射到相應的 payment_method_code
        method_mapping = {
            'vacc': 'bank_transfer',
            'ibon': '7eleven',
            'fami': 'fami',
        }
        return {method_mapping.get(self.smilepay_payment_method, 'bank_transfer')}
    
    def _smilepay_get_api_url(self):
        """ Return the API URL according to the environment.

        :return: The API URL
        :rtype: str
        """
        self.ensure_one()
        if self.smilepay_environment == 'prod':
            return 'https://ssl.smse.com.tw/api/SPPayment.asp'
        else:
            return 'https://ssl.smse.com.tw/api/SPPayment.asp'  # 文件沒有提供測試環境URL，使用相同URL