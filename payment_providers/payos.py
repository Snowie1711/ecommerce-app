import hmac
import hashlib
import json
import requests
from datetime import datetime
from flask import current_app

class PayOSAPI:
    """PayOS payment integration"""
    
    def __init__(self):
        """Initialize PayOS payment with config validation"""
        required_configs = [
            'PAYOS_CLIENT_ID',
            'PAYOS_API_KEY',
            'PAYOS_CHECKSUM_KEY'
        ]
        
        # Verify all required configs are present
        missing_configs = [config for config in required_configs
                         if not current_app.config.get(config)]
        
        if missing_configs:
            error_msg = f"Missing PayOS configurations: {', '.join(missing_configs)}"
            current_app.logger.error(error_msg)
            raise ValueError(error_msg)
            
        self.client_id = current_app.config['PAYOS_CLIENT_ID']
        self.api_key = current_app.config['PAYOS_API_KEY']
        self.checksum_key = current_app.config['PAYOS_CHECKSUM_KEY']
        self.base_url = "https://api-merchant.payos.vn/v2"
        self.api_endpoint = f"{self.base_url}/payment-requests"

    def create_payment(self, order_id: str, amount: int, description: str) -> dict:
        """
        Create a PayOS payment request
        
        Args:
            order_id: Unique order identifier
            amount: Payment amount in VND
            description: Order description
            
        Returns:
            Dict containing payment URL and order data
        """
        try:
            request_id = f"REQ_{datetime.now().strftime('%Y%m%d%H%M%S')}_{order_id}"
            
            # Prepare consistent description
            description = f"Payment for order {order_id}"
            cancel_url = f"{current_app.config['BASE_URL']}/payment/payment-result"
            return_url = f"{current_app.config['BASE_URL']}/payment/payment-result"

            # Prepare payment data with fields in alphabetical order
            payment_data = {
                "amount": amount,
                "cancelUrl": cancel_url,
                "description": description,
                "orderCode": str(order_id),
                "returnUrl": return_url
            }

            # Generate signature and log details for debugging
            signature = self._generate_signature(order_id, amount)
            
            # Log full request details
            current_app.logger.info(f"""
            PayOS Payment Request Details:
            ============================
            Order ID: {order_id}
            Amount: {amount} (type: {type(amount)})
            Description: {description}
            Cancel URL: {current_app.config['BASE_URL']}/payment/payment-result
            Return URL: {current_app.config['BASE_URL']}/payment/payment-result
            Generated Signature: {signature}
            
            Full Payment Data:
            {json.dumps(payment_data, indent=2)}
            ============================
            """)
            
            payment_data["signature"] = signature

            # Make API request
            response = requests.post(
                self.api_endpoint,
                json=payment_data,
                headers={
                    'x-client-id': self.client_id,
                    'x-api-key': self.api_key,
                    'Content-Type': 'application/json'
                },
                timeout=30
            )

            # Log raw response
            current_app.logger.info(f"""
            PayOS API Response:
            ==================
            Status Code: {response.status_code}
            Response Headers: {dict(response.headers)}
            Response Body: {response.text}
            ==================
            """)

            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('code') == '00':
                        return {
                            "success": True,
                            "payment_url": result['data']['checkoutUrl'],
                            "request_id": request_id
                        }
                    else:
                        error_msg = result.get('desc', 'Unknown PayOS error')
                        current_app.logger.error(f"""
                        PayOS API Error:
                        Error Message: {error_msg}
                        Response Code: {result.get('code')}
                        Full Response: {json.dumps(result, indent=2)}
                        """)
                        return {
                            "success": False,
                            "error": f"PayOS error: {error_msg}"
                        }
                except json.JSONDecodeError as e:
                    current_app.logger.error(f"Failed to parse PayOS response: {str(e)}")
                    return {
                        "success": False,
                        "error": "Invalid response from payment server"
                    }

            current_app.logger.error(f"PayOS API request failed: {response.status_code}")
            return {
                "success": False,
                "error": "Payment system error. Please try again."
            }

        except Exception as e:
            current_app.logger.error(f"PayOS payment creation error: {str(e)}")
            return {
                "success": False,
                "error": "An error occurred while creating the payment"
            }

    def get_payment_info(self, payment_id: str) -> dict:
        """
        Get payment information from PayOS
        
        Args:
            payment_id: Payment request ID
            
        Returns:
            Dict containing payment information or error
        """
        try:
            # Make API request
            response = requests.get(
                f"{self.api_endpoint}/{payment_id}",
                headers={
                    'x-client-id': self.client_id,
                    'x-api-key': self.api_key
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == '00':
                    return {
                        "success": True,
                        "data": result['data']
                    }
                else:
                    error_msg = result.get('desc', 'Unknown PayOS error')
                    current_app.logger.error(f"PayOS API error: {error_msg}")
                    return {
                        "success": False,
                        "error": f"PayOS error: {error_msg}"
                    }

            current_app.logger.error(f"PayOS API request failed: {response.status_code}")
            return {
                "success": False,
                "error": "Payment information request failed"
            }

        except Exception as e:
            current_app.logger.error(f"PayOS payment info error: {str(e)}")
            return {
                "success": False,
                "error": "Error retrieving payment information"
            }

    def cancel_payment(self, payment_id: str) -> dict:
        """
        Cancel a payment request
        
        Args:
            payment_id: Payment request ID to cancel
            
        Returns:
            Dict containing cancel result or error
        """
        try:
            # Make API request
            response = requests.post(
                f"{self.api_endpoint}/{payment_id}/cancel",
                headers={
                    'x-client-id': self.client_id,
                    'x-api-key': self.api_key,
                    'Content-Type': 'application/json'
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == '00':
                    return {
                        "success": True,
                        "message": "Payment cancelled successfully"
                    }
                else:
                    error_msg = result.get('desc', 'Unknown PayOS error')
                    current_app.logger.error(f"PayOS API error: {error_msg}")
                    return {
                        "success": False,
                        "error": f"PayOS error: {error_msg}"
                    }

            current_app.logger.error(f"PayOS API request failed: {response.status_code}")
            return {
                "success": False,
                "error": "Payment cancellation failed"
            }

        except Exception as e:
            current_app.logger.error(f"PayOS payment cancellation error: {str(e)}")
            return {
                "success": False,
                "error": "Error cancelling payment"
            }

    def verify_webhook(self, webhook_data: dict) -> bool:
        """
        Verify the webhook data from PayOS
        
        Args:
            webhook_data: Webhook data received from PayOS
            
        Returns:
            bool: True if verification succeeds, False otherwise
        """
        try:
            signature = webhook_data.pop('signature', '')
            
            # Create signature string from webhook data
            data_to_sign = f"{webhook_data['orderCode']}{webhook_data['amount']}{webhook_data['status']}"
            
            # Calculate HMAC
            calculated_signature = hmac.new(
                self.checksum_key.encode(),
                data_to_sign.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, calculated_signature)
            
        except Exception as e:
            current_app.logger.error(f"PayOS webhook verification error: {str(e)}")
            return False

    def _generate_signature(self, order_id: str, amount: int) -> str:
        """
        Generate signature for payment request according to PayOS specification
        Format: amount|cancelUrl|description|orderCode|returnUrl
        """
        try:
            # Prepare signature data with sorted field order
            cancel_url = f"{current_app.config['BASE_URL']}/payment/payment-result"
            return_url = f"{current_app.config['BASE_URL']}/payment/payment-result"
            description = f"Payment for order {order_id}"
            order_code = str(order_id)
            
            # Create signature string with fields in alphabetical order
            signature_parts = [
                str(amount),          # amount
                cancel_url,           # cancelUrl
                description,          # description
                order_code,           # orderCode
                return_url           # returnUrl
            ]
            
            # Join with | separator
            data_string = "|".join(signature_parts)
            # Generate HMAC SHA256 signature
            signature = hmac.new(
                self.checksum_key.encode('utf-8'),
                data_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            # Log signature data for debugging
            current_app.logger.info(f"""
            PayOS Signature Generation:
            ========================
            Input Values:
            Amount: {amount} (type: {type(amount)})
            Cancel URL: {cancel_url}
            Description: {description}
            Order Code: {order_code}
            Return URL: {return_url}
            
            Signature String: {data_string}
            Checksum Key (first 10): {self.checksum_key[:10]}...
            
            Generated HMAC-SHA256: {signature}
            ========================
            """)
            
            return signature
            
            return signature
            
        except Exception as e:
            current_app.logger.error(f"Error generating PayOS signature: {str(e)}")
            raise