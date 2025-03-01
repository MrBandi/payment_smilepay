import logging
import hashlib
import pprint
import requests
import time
from datetime import datetime, timedelta
from werkzeug import urls
from xml.etree import ElementTree as ET

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    smilepay_payment_no = fields.Char(string='SmilePay 付款號碼', readonly=True)
    smilepay_atm_bank_no = fields.Char(string='ATM 銀行代碼', readonly=True)
    smilepay_atm_no = fields.Char(string='ATM 虛擬帳號', readonly=True)
    smilepay_ibon_no = fields.Char(string='ibon 繳費代碼', readonly=True)
    smilepay_fami_no = fields.Char(string='FamilyMart 繳費代碼', readonly=True)
    smilepay_barcode1 = fields.Char(string='條碼1', readonly=True)
    smilepay_barcode2 = fields.Char(string='條碼2', readonly=True)
    smilepay_barcode3 = fields.Char(string='條碼3', readonly=True)
    smilepay_payment_url = fields.Char(string='付款網址', readonly=True)
    smilepay_expire_date = fields.Datetime(string='繳費期限', readonly=True)

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return SmilePay-specific rendering values.

        Note: self.ensure_one() from the parent method.

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'smilepay':
            return res
        
        # 呼叫 SmilePay API 取得付款資訊
        payment_data = self._smilepay_get_payment_data()
        
        # 更新渲染值
        return {
            'api_url': self.provider_id._smilepay_get_api_url(),
            'payment_data': payment_data,
            'tx_reference': self.reference,
            'smilepay_payment_method': self.provider_id.smilepay_payment_method,
        }

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return SmilePay-specific processing values.

        Note: self.ensure_one() from the parent method.

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'smilepay':
            return res
        
        # 在這裡可以添加需要傳遞給其他方法的處理值
        return res

    def _smilepay_get_payment_data(self):
        """ Generate and return the data for SmilePay API.
        
        :return: The data dict
        :rtype: dict
        """
        self.ensure_one()
        
        # 設定付款期限（預設7天）
        expire_date = datetime.now() + timedelta(days=7)
        expire_date_str = expire_date.strftime('%Y/%m/%d')
        expire_time_str = expire_date.strftime('%H:%M:%S')
        
        # 設定付款方式代碼
        payment_method_mapping = {
            'vacc': '2',  # 虛擬帳號/ATM
            'ibon': '4',  # 7-11 ibon
            'fami': '6',  # FamiPort
        }
        pay_zg = payment_method_mapping.get(self.provider_id.smilepay_payment_method, '2')
        
        # 設定回調URL
        base_url = self.provider_id.get_base_url()
        notify_url = urls.url_join(base_url, '/payment/smilepay/notify')
        
        # 準備 API 參數
        params = {
            'Dcvc': self.provider_id.smilepay_merchant_id,
            'Rvg2c': self.provider_id.smilepay_parameter_code,
            'Verify_key': self.provider_id.smilepay_verify_key,
            'Od_sob': f'Order {self.reference}',
            'Pay_zg': pay_zg,
            'Data_id': self.reference,
            'Deadline_date': expire_date_str,
            'Deadline_time': expire_time_str,
            'Amount': int(self.amount),
            'Pur_name': self.partner_name or '',
            'Tel_number': self.partner_phone or '',
            'Mobile_number': self.partner_phone or '',
            'Email': self.partner_email or '',
            'Roturl': notify_url,
            'Roturl_status': 'RL_OK'
        }
        
        _logger.info(f"SmilePay API request params: {pprint.pformat(params)}")
        
        # 呼叫 SmilePay API
        try:
            response = requests.get(self.provider_id._smilepay_get_api_url(), params=params)
            _logger.info(f"SmilePay API response: {response.text}")
            
            if response.status_code != 200:
                _logger.error(f"SmilePay API error: {response.status_code} {response.text}")
                raise ValidationError(_("SmilePay API error: %s", response.text))
            
            # 解析 XML 回應
            payment_info = self._smilepay_parse_response(response.text)
            
            # 保存付款資訊到交易紀錄
            self._smilepay_save_payment_info(payment_info)
            
            return payment_info
            
        except Exception as e:
            _logger.exception(f"SmilePay API call failed: {str(e)}")
            raise ValidationError(_("SmilePay API call failed: %s", str(e)))
    
    def _smilepay_parse_response(self, response_text):
        """ Parse the XML response from SmilePay API.
        
        :param str response_text: The API response text
        :return: The parsed payment info
        :rtype: dict
        """
        try:
            root = ET.fromstring(response_text)
            
            # 檢查狀態碼
            status = root.find('Status').text
            if status != '1':
                error_desc = root.find('Desc').text
                _logger.error(f"SmilePay API error: {status} {error_desc}")
                raise ValidationError(_("SmilePay API error: %s", error_desc))
            
            # 解析付款資訊
            payment_info = {
                'Status': status,
                'Desc': root.find('Desc').text,
                'SmilePayNO': root.find('SmilePayNO').text,
                'Amount': root.find('Amount').text,
            }
            
            # 根據付款方式取得對應的付款資訊
            payment_method = self.provider_id.smilepay_payment_method
            
            # ATM 虛擬帳號
            if payment_method == 'vacc':
                atm_bank_no = root.find('AtmBankNo')
                atm_no = root.find('AtmNo')
                
                if atm_bank_no is not None and atm_no is not None:
                    payment_info['AtmBankNo'] = atm_bank_no.text
                    payment_info['AtmNo'] = atm_no.text
            
            # 7-11 ibon
            elif payment_method == 'ibon':
                ibon_no = root.find('IbonNo')
                
                if ibon_no is not None:
                    payment_info['IbonNo'] = ibon_no.text
            
            # FamilyMart FamiPort
            elif payment_method == 'fami':
                fami_no = root.find('FamiNO')
                
                if fami_no is not None:
                    payment_info['FamiNO'] = fami_no.text
            
            # 繳費期限
            pay_end_date = root.find('PayEndDate')
            if pay_end_date is not None:
                payment_info['PayEndDate'] = pay_end_date.text
            
            # 條碼 (超商繳費單)
            barcode1 = root.find('Barcode1')
            barcode2 = root.find('Barcode2')
            barcode3 = root.find('Barcode3')
            
            if barcode1 is not None and barcode2 is not None and barcode3 is not None:
                payment_info['Barcode1'] = barcode1.text
                payment_info['Barcode2'] = barcode2.text
                payment_info['Barcode3'] = barcode3.text
            
            return payment_info
            
        except ET.ParseError as e:
            _logger.exception(f"Failed to parse SmilePay API response: {e}")
            raise ValidationError(_("無法解析 SmilePay API 回應"))
    
    def _smilepay_save_payment_info(self, payment_info):
        """ Save the SmilePay payment info to the transaction.
        
        :param dict payment_info: The payment info from SmilePay API
        :return: None
        """
        self.ensure_one()
        payment_values = {
            'provider_reference': payment_info.get('SmilePayNO'),
            'smilepay_payment_no': payment_info.get('SmilePayNO'),
        }
        
        # 設定繳費期限
        pay_end_date = payment_info.get('PayEndDate')
        if pay_end_date:
            try:
                payment_values['smilepay_expire_date'] = datetime.strptime(
                    pay_end_date, '%Y/%m/%d'
                )
            except ValueError:
                _logger.warning(f"Invalid PayEndDate format: {pay_end_date}")
        
        # 根據付款方式儲存對應的付款資訊
        payment_method = self.provider_id.smilepay_payment_method
        
        # ATM 虛擬帳號
        if payment_method == 'vacc':
            payment_values.update({
                'smilepay_atm_bank_no': payment_info.get('AtmBankNo'),
                'smilepay_atm_no': payment_info.get('AtmNo'),
            })
        
        # 7-11 ibon
        elif payment_method == 'ibon':
            payment_values['smilepay_ibon_no'] = payment_info.get('IbonNo')
        
        # FamilyMart FamiPort
        elif payment_method == 'fami':
            payment_values['smilepay_fami_no'] = payment_info.get('FamiNO')
        
        # 條碼 (超商繳費單)
        if all(key in payment_info for key in ['Barcode1', 'Barcode2', 'Barcode3']):
            payment_values.update({
                'smilepay_barcode1': payment_info.get('Barcode1'),
                'smilepay_barcode2': payment_info.get('Barcode2'),
                'smilepay_barcode3': payment_info.get('Barcode3'),
            })
        
        # 更新交易紀錄
        self.write(payment_values)
        
        # 更新交易狀態為處理中
        self._set_pending()
    
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on SmilePay data.
        
        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The corresponding transaction, if any
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'smilepay' or len(tx) == 1:
            return tx
        
        # 從 SmilePay 回調獲取訂單號碼
        data_id = notification_data.get('Data_id')
        smilepay_no = notification_data.get('Smseid')
        
        if data_id:
            tx = self.search([('reference', '=', data_id), ('provider_code', '=', 'smilepay')])
        elif smilepay_no:
            tx = self.search([
                ('provider_reference', '=', smilepay_no), 
                ('provider_code', '=', 'smilepay')
            ])
        
        if not tx:
            error_msg = _(
                "SmilePay: No transaction found matching reference %s or SmilePay NO %s.",
                data_id, smilepay_no
            )
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        
        return tx
    
    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on SmilePay data.
        
        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'smilepay':
            return
        
        # 判斷交易狀態
        classif = notification_data.get('Classif')
        response_id = notification_data.get('Response_id')
        process_date = notification_data.get('Process_date')
        amount = notification_data.get('Amount')
        
        # 將交易標記為完成
        if response_id == '1' or (classif in ['B', 'E', 'F'] and amount):
            self._set_done()
        # 其他情況保持為處理中
        else:
            self._set_pending()