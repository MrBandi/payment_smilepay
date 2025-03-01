# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class SmilePayController(http.Controller):
    _notify_url = '/payment/smilepay/notify'
    
    @http.route(_notify_url, type='http', auth='public', methods=['POST'], csrf=False)
    def smilepay_notify(self, **post):
        """ Process the notification data sent by SmilePay after payment.
        
        :param dict post: The notification data
        :return: A response to the notification
        :rtype: str
        """
        _logger.info("接收到 SmilePay 通知: %s", pprint.pformat(post))
        
        # 驗證通知數據
        if not post:
            _logger.warning("收到空的 SmilePay 通知數據")
            return 'NO PARAMETERS'
        
        # 處理通知
        try:
            # 驗證 SmilePay 驗證碼
            if 'Mid_smilepay' in post:
                # 在實際應用中，需要實現檢查 Mid_smilepay 的邏輯
                pass
            
            # 獲取和處理交易
            request.env['payment.transaction'].sudo()._handle_notification_data('smilepay', post)
            
            # 依照 SmilePay 規格返回 Roturl_status 參數，表示成功接收通知
            return '<Roturlstatus>RL_OK</Roturlstatus>'
            
        except ValidationError as e:
            _logger.exception("無法處理 SmilePay 通知: %s", str(e))
            return 'ERROR'