# -*- coding: utf-8 -*-

import logging
import pprint
from werkzeug import urls

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class SmilePayController(http.Controller):
    
    @http.route('/payment/smilepay/callback/<string:payment_method_code>', type='http', auth='public', csrf=False, save_session=False)
    def smilepay_callback(self, payment_method_code, **post):
        """ 處理SmilePay支付回調 """
        _logger.info(f"收到SmilePay回調: {pprint.pformat(post)}")
        
        # 驗證回調資料
        if not post:
            return "資料為空"
            
        # 根據不同支付方式驗證回調
        if payment_method_code == 'smilepay_atm':
            return self._handle_atm_callback(post)
        elif payment_method_code == 'smilepay_barcode':
            return self._handle_barcode_callback(post)
        elif payment_method_code == 'smilepay_ibon':
            return self._handle_ibon_callback(post)
        elif payment_method_code == 'smilepay_famiport':
            return self._handle_famiport_callback(post)
        
        return "未知的支付方式"
        
    def _handle_atm_callback(self, post):
        """處理ATM轉帳回調"""
        if post.get('Classif') != 'B' or not all(key in post for key in ['Od_sob', 'Payment_no', 'Purchamt', 'Smseid', 'Mid_smilepay']):
            _logger.warning("ATM回調缺少必要參數")
            return "0"
            
        # 查找交易
        tx_reference = post.get('Od_sob')
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', tx_reference)], limit=1)
        
        if not tx_sudo or tx_sudo.provider_code != 'smilepay' or tx_sudo.payment_method_code != 'smilepay_atm':
            _logger.warning(f"找不到相符的ATM交易: {tx_reference}")
            return "0"
            
        # 驗證金額和支付代碼
        if tx_sudo.smilepay_atm_no != post.get('Payment_no') or int(tx_sudo.amount) != int(post.get('Purchamt')):
            _logger.warning(f"ATM交易資料不匹配: {tx_reference}")
            return "0"
            
        # 驗證mid_smilepay
        provider = tx_sudo.provider_id
        calculated_mid = provider._smilepay_calculate_mid_smilepay(
            provider.smilepay_smseid, 
            post.get('Purchamt'), 
            post.get('Smseid')
        )
        
        if str(calculated_mid) != post.get('Mid_smilepay'):
            _logger.warning(f"ATM交易驗證碼不匹配: {tx_reference}")
            return "0"
            
        # 確認付款
        tx_sudo._set_done()
        
        return "<Roturlstatus>Payment_OK</Roturlstatus>"
        
    def _handle_barcode_callback(self, post):
        """處理超商條碼回調"""
        if post.get('Classif') != 'C' or not all(key in post for key in ['Od_sob', 'Purchamt', 'Smseid', 'Mid_smilepay']):
            _logger.warning("超商條碼回調缺少必要參數")
            return "0"
            
        # 查找交易
        tx_reference = post.get('Od_sob')
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', tx_reference)], limit=1)
        
        if not tx_sudo or tx_sudo.provider_code != 'smilepay' or tx_sudo.payment_method_code != 'smilepay_barcode':
            _logger.warning(f"找不到相符的超商條碼交易: {tx_reference}")
            return "0"
            
        # 驗證金額
        if int(tx_sudo.amount) != int(post.get('Purchamt')):
            _logger.warning(f"超商條碼交易金額不匹配: {tx_reference}")
            return "0"
            
        # 驗證mid_smilepay
        provider = tx_sudo.provider_id
        calculated_mid = provider._smilepay_calculate_mid_smilepay(
            provider.smilepay_smseid, 
            post.get('Purchamt'), 
            post.get('Smseid')
        )
        
        if str(calculated_mid) != post.get('Mid_smilepay'):
            _logger.warning(f"超商條碼交易驗證碼不匹配: {tx_reference}")
            return "0"
            
        # 確認付款
        tx_sudo._set_done()
        
        return "<Roturlstatus>Payment_OK</Roturlstatus>"
        
    def _handle_ibon_callback(self, post):
        """處理ibon回調"""
        if post.get('Classif') != 'E' or not all(key in post for key in ['Od_sob', 'Payment_no', 'Purchamt', 'Smseid', 'Mid_smilepay']):
            _logger.warning("ibon回調缺少必要參數")
            return "0"
            
        # 查找交易
        tx_reference = post.get('Od_sob')
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', tx_reference)], limit=1)
        
        if not tx_sudo or tx_sudo.provider_code != 'smilepay' or tx_sudo.payment_method_code != 'smilepay_ibon':
            _logger.warning(f"找不到相符的ibon交易: {tx_reference}")
            return "0"
            
        # 驗證金額和支付代碼
        if tx_sudo.smilepay_ibon_no != post.get('Payment_no') or int(tx_sudo.amount) != int(post.get('Purchamt')):
            _logger.warning(f"ibon交易資料不匹配: {tx_reference}")
            return "0"
            
        # 驗證mid_smilepay
        provider = tx_sudo.provider_id
        calculated_mid = provider._smilepay_calculate_mid_smilepay(
            provider.smilepay_smseid, 
            post.get('Purchamt'), 
            post.get('Smseid')
        )
        
        if str(calculated_mid) != post.get('Mid_smilepay'):
            _logger.warning(f"ibon交易驗證碼不匹配: {tx_reference}")
            return "0"
            
        # 確認付款
        tx_sudo._set_done()
        
        return "<Roturlstatus>Payment_OK</Roturlstatus>"
        
    def _handle_famiport_callback(self, post):
        """處理全家FamiPort回調"""
        if post.get('Classif') != 'F' or not all(key in post for key in ['Od_sob', 'Payment_no', 'Purchamt', 'Smseid', 'Mid_smilepay']):
            _logger.warning("FamiPort回調缺少必要參數")
            return "0"
            
        # 查找交易
        tx_reference = post.get('Od_sob')
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', tx_reference)], limit=1)
        
        if not tx_sudo or tx_sudo.provider_code != 'smilepay' or tx_sudo.payment_method_code != 'smilepay_famiport':
            _logger.warning(f"找不到相符的FamiPort交易: {tx_reference}")
            return "0"
            
        # 驗證金額和支付代碼
        if tx_sudo.smilepay_fami_no != post.get('Payment_no') or int(tx_sudo.amount) != int(post.get('Purchamt')):
            _logger.warning(f"FamiPort交易資料不匹配: {tx_reference}")
            return "0"
            
        # 驗證mid_smilepay
        provider = tx_sudo.provider_id
        calculated_mid = provider._smilepay_calculate_mid_smilepay(
            provider.smilepay_smseid, 
            post.get('Purchamt'), 
            post.get('Smseid')
        )
        
        if str(calculated_mid) != post.get('Mid_smilepay'):
            _logger.warning(f"FamiPort交易驗證碼不匹配: {tx_reference}")
            return "0"
            
        # 確認付款
        tx_sudo._set_done()
        
        return "<Roturlstatus>Payment_OK</Roturlstatus>"