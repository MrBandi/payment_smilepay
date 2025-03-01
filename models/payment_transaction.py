# -*- coding: utf-8 -*-

import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    smilepay_no = fields.Char("SmilePay訂單編號", readonly=True)
    smilepay_atm_bank_no = fields.Char("銀行代號", readonly=True)
    smilepay_atm_no = fields.Char("銀行帳號", readonly=True)
    smilepay_barcode1 = fields.Char("繳費條碼1", readonly=True)
    smilepay_barcode2 = fields.Char("繳費條碼2", readonly=True)
    smilepay_barcode3 = fields.Char("繳費條碼3", readonly=True)
    smilepay_ibon_no = fields.Char("ibon代碼", readonly=True)
    smilepay_fami_no = fields.Char("全家代碼", readonly=True)
    smilepay_pay_end_date = fields.Datetime("繳費期限", readonly=True)

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return SmilePay-specific rendering values.
        
        Note: self.ensure_one() from inherited method
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'smilepay':
            return res

        _logger.info(f"Getting rendering values for SmilePay transaction: {self.reference} with method: {self.payment_method_code}")
        
        # 生成支付資訊
        self._generate_smilepay_payment_info()
        payment_method_code = self.payment_method_code
        
        # 根據不同的支付方式生成對應的顯示數據
        rendering_values = {'tx_id': self.id}
        
        if payment_method_code == 'smilepay_atm':
            rendering_values.update({
                'atm_bank_no': self.smilepay_atm_bank_no,
                'atm_no': self.smilepay_atm_no,
                'pay_end_date': self.smilepay_pay_end_date,
                'amount': int(self.amount),
                'qrcode_url': self._get_atm_qrcode_url(),
            })
        elif payment_method_code == 'smilepay_barcode':
            rendering_values.update({
                'barcode1': self.smilepay_barcode1,
                'barcode2': self.smilepay_barcode2,
                'barcode3': self.smilepay_barcode3,
                'pay_end_date': self.smilepay_pay_end_date,
                'amount': int(self.amount),
            })
        elif payment_method_code == 'smilepay_ibon':
            rendering_values.update({
                'ibon_no': self.smilepay_ibon_no,
                'pay_end_date': self.smilepay_pay_end_date,
                'amount': int(self.amount),
                'qrcode_url': self._get_ibon_qrcode_url(),
            })
        elif payment_method_code == 'smilepay_famiport':
            rendering_values.update({
                'fami_no': self.smilepay_fami_no,
                'pay_end_date': self.smilepay_pay_end_date,
                'amount': int(self.amount),
            })
        
        _logger.info(f"SmilePay rendering values: {rendering_values}")
        return rendering_values

    def _get_atm_qrcode_url(self):
        """生成ATM轉帳QR碼URL"""
        if not self.smilepay_atm_no or not self.smilepay_atm_bank_no:
            return False
            
        bank_pay_end_date = self.smilepay_pay_end_date.strftime('%Y%m%d%H%M%S') if self.smilepay_pay_end_date else ''
        amount = int(self.amount)
        qrcode_content = f"TWQRP://台灣銀行轉帳/158/02/V1?D1={amount}00&D5={self.smilepay_atm_bank_no}&D6={self.smilepay_atm_no}&D12={bank_pay_end_date}"
        
        return f"https://payment-code.atomroute.com/qrcode.php?code={urls.url_quote_plus(qrcode_content)}"
    
    def _get_ibon_qrcode_url(self):
        """生成ibon QR碼URL"""
        if not self.smilepay_ibon_no:
            return False
            
        return f"https://payment-code.atomroute.com/qrcode.php?code={urls.url_quote_plus(self.smilepay_ibon_no)}"

    def _generate_smilepay_payment_info(self):
        """生成SmilePay支付資訊"""
        self.ensure_one()
        
        _logger.info(f"Generating SmilePay payment info for transaction {self.reference}")
        
        # 檢查是否已經有支付資訊
        if self._check_existing_payment_info():
            _logger.info(f"Payment info already exists for transaction {self.reference}")
            return
            
        # 獲取提供者和交易資訊
        provider = self.provider_id
        payment_method_code = self.payment_method_code
        
        if not provider.smilepay_rvg2c or not provider.smilepay_dcvc or not provider.smilepay_verify_key:
            _logger.error(f"SmilePay configuration incomplete for provider ID {provider.id}")
            raise ValidationError(_("SmilePay 配置不完整。請確保已正確設置參數碼、商家代號和檢查碼。"))
        
        # 設置API參數
        base_api_url = 'https://ssl.smse.com.tw/api/SPPayment.asp'
        roturl = f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/payment/smilepay/callback/{payment_method_code}"
        
        _logger.info(f"SmilePay callback URL: {roturl}")
        
        # 根據支付方式設置pay_zg值
        pay_zg = {
            'smilepay_atm': '2',
            'smilepay_barcode': '3',
            'smilepay_ibon': '4',
            'smilepay_famiport': '6',
        }[payment_method_code]
        
        # 準備API參數
        api_params = {
            'Rvg2c': provider.smilepay_rvg2c,
            'Dcvc': provider.smilepay_dcvc,
            'Od_sob': self.reference,
            'Amount': int(self.amount),
            'Pur_name': self.partner_name or 'N/A',
            'Mobile_number': self.partner_phone or 'N/A',
            'Email': self.partner_email or 'N/A',
            'Remark': f'Odoo訂單 {self.reference}',
            'Roturl': roturl,
            'Roturl_status': 'Payment_OK',
            'Pay_zg': pay_zg,
            'Verify_key': provider.smilepay_verify_key
        }
        
        _logger.info(f"SmilePay API parameters: {api_params}")
        
        # 呼叫API
        try:
            api_url = f"{base_api_url}?{urls.url_encode(api_params)}"
            _logger.info(f"Calling SmilePay API: {api_url}")
            
            response = requests.get(api_url, timeout=10)
            _logger.info(f"SmilePay API response status: {response.status_code}")
            
            if response.status_code != 200:
                _logger.error(f"SmilePay API錯誤: HTTP狀態碼 {response.status_code}")
                _logger.error(f"SmilePay API response content: {response.content}")
                raise ValidationError(_("無法連接到SmilePay服務。"))
                
            # 記錄響應內容以便調試
            _logger.info(f"SmilePay API response: {response.content}")
                
            # 解析XML響應
            xml_data = ET.fromstring(response.content)
            status = xml_data.find('Status').text
            
            if status != '1':
                error_msg = xml_data.find('Desc').text if xml_data.find('Desc') is not None else "未知錯誤"
                _logger.error(f"SmilePay API錯誤: {error_msg}")
                raise ValidationError(_("SmilePay處理錯誤: %s", error_msg))
                
            # 更新交易的支付資訊
            update_vals = {
                'smilepay_no': xml_data.find('SmilePayNO').text,
            }
            
            # 如果PayEndDate存在，則解析它
            pay_end_date_elem = xml_data.find('PayEndDate')
            if pay_end_date_elem is not None and pay_end_date_elem.text:
                try:
                    update_vals['smilepay_pay_end_date'] = datetime.strptime(pay_end_date_elem.text, '%Y/%m/%d %H:%M:%S')
                except ValueError as e:
                    _logger.warning(f"無法解析PayEndDate '{pay_end_date_elem.text}': {str(e)}")
            
            # 根據支付方式提取特定資訊
            if payment_method_code == 'smilepay_atm':
                atm_bank_no = xml_data.find('AtmBankNo')
                atm_no = xml_data.find('AtmNo')
                if atm_bank_no is not None and atm_no is not None:
                    update_vals.update({
                        'smilepay_atm_bank_no': atm_bank_no.text,
                        'smilepay_atm_no': atm_no.text,
                    })
            elif payment_method_code == 'smilepay_barcode':
                barcode1 = xml_data.find('Barcode1')
                barcode2 = xml_data.find('Barcode2')
                barcode3 = xml_data.find('Barcode3')
                if barcode1 is not None and barcode2 is not None and barcode3 is not None:
                    update_vals.update({
                        'smilepay_barcode1': barcode1.text,
                        'smilepay_barcode2': barcode2.text,
                        'smilepay_barcode3': barcode3.text,
                    })
            elif payment_method_code == 'smilepay_ibon':
                ibon_no = xml_data.find('IbonNo')
                if ibon_no is not None:
                    update_vals.update({
                        'smilepay_ibon_no': ibon_no.text,
                    })
            elif payment_method_code == 'smilepay_famiport':
                fami_no = xml_data.find('FamiNO')
                if fami_no is not None:
                    update_vals.update({
                        'smilepay_fami_no': fami_no.text,
                    })
                
            _logger.info(f"Updating transaction {self.reference} with values: {update_vals}")
            self.write(update_vals)
            self._set_pending(state_message="等待付款中")
            
        except Exception as e:
            _logger.exception(f"SmilePay處理異常: {str(e)}")
            raise ValidationError(_("處理SmilePay支付請求時出錯: %s", str(e)))

    def _check_existing_payment_info(self):
        """檢查是否已經存在支付資訊"""
        self.ensure_one()
        payment_method_code = self.payment_method_code
        
        if payment_method_code == 'smilepay_atm':
            return bool(self.smilepay_atm_no)
        elif payment_method_code == 'smilepay_barcode':
            return bool(self.smilepay_barcode1)
        elif payment_method_code == 'smilepay_ibon':
            return bool(self.smilepay_ibon_no)
        elif payment_method_code == 'smilepay_famiport':
            return bool(self.smilepay_fami_no)
        return False