/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import checkoutForm from "@payment/js/checkout_form";
import { formWidget } from "@payment/js/payment_form";

const smilePayMixin = {
    /**
     * @override
     */
    updateNewPaymentDisplayStatus: function () {
        this._super.apply(this, arguments);
        
        // 檢查是否選擇了 SmilePay 付款方式
        const checkedRadio = this.el.querySelector('input[type="radio"]:checked');
        if (checkedRadio && checkedRadio.dataset.providerCode === 'smilepay') {
            // 更新提交按鈕文字
            const submitButton = this.el.querySelector('button[name="o_payment_submit_button"]');
            if (submitButton) {
                submitButton.textContent = _t("取得付款資訊");
            }
        }
    },
};

checkoutForm.include(smilePayMixin);
formWidget.include(smilePayMixin);