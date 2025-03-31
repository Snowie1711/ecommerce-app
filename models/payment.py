import hmac
import hashlib
import json
import requests
import random
from datetime import datetime
from time import time
from typing import Dict, Any
from flask import current_app
from flask_login import current_user

class MoMoPayment:
    @staticmethod
    def validate_config():
        """Validate MoMo configuration and test connection"""
        from flask import current_app
        
        required_configs = [
            'MOMO_PARTNER_CODE',
            'MOMO_ACCESS_KEY',
            'MOMO_SECRET_KEY',
            'MOMO_PAYMENT_URL',
            'MOMO_REDIRECT_URL',
            'MOMO_IPN_URL'
        ]
        
        # Check all required configs
        for config in required_configs:
            if not current_app.config.get(config):
                current_app.logger.error(f"Missing MoMo config: {config}")
                return False
            
        # Test MoMo connection
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            response = requests.get(
                current_app.config['MOMO_PAYMENT_URL'].split('/gw_payment')[0] + '/api/status',
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                current_app.logger.info("MoMo connection test successful")
                return True
            else:
                current_app.logger.error(f"MoMo connection test failed: Status {response.status_code}")
                return False
        except Exception as e:
            current_app.logger.error(f"MoMo connection test failed: {str(e)}")
            return False

    def __init__(self):
        """Initialize MoMo payment with config validation"""
        required_configs = [
            'MOMO_PARTNER_CODE',
            'MOMO_ACCESS_KEY',
            'MOMO_SECRET_KEY',
            'MOMO_PAYMENT_URL',
            'MOMO_REDIRECT_URL',
            'MOMO_IPN_URL'
        ]
        
        # Verify all required configs are present
        missing_configs = [config for config in required_configs
                         if not current_app.config.get(config)]
        
        if missing_configs:
            error_msg = f"Missing MoMo configurations: {', '.join(missing_configs)}"
            current_app.logger.error(error_msg)
            raise ValueError(error_msg)
            
        try:
            self.partner_code = current_app.config['MOMO_PARTNER_CODE']
            self.access_key = current_app.config['MOMO_ACCESS_KEY']
            self.secret_key = current_app.config['MOMO_SECRET_KEY']
            self.payment_url = current_app.config['MOMO_PAYMENT_URL']
            
            # Log successful initialization
            current_app.logger.info(f"""
            === MoMo Configuration ===
            Partner Code: {self.partner_code}
            Payment URL: {self.payment_url}
            Redirect URL: {current_app.config['MOMO_REDIRECT_URL']}
            IPN URL: {current_app.config['MOMO_IPN_URL']}
            """)
            
        except Exception as e:
            error_msg = f"Error initializing MoMo payment: {str(e)}"
            current_app.logger.error(error_msg)
            raise ValueError(error_msg)

    def create_order(self, order_id: str, amount: int, description: str) -> Dict[str, Any]:
        """
        Create a MoMo payment order
        
        Args:
            order_id: Unique order identifier
            amount: Payment amount in VND
            description: Order description
            
        Returns:
            Dict containing payment URL and order data
        """
        # First validate configuration and test connection
        try:
            current_app.logger.info("=== Starting MoMo Payment Creation ===")
            current_app.logger.info(f"Order ID: {order_id}, Amount: {amount}")
            
            if not self.validate_config():
                error_msg = "MoMo configuration validation failed"
                current_app.logger.error(error_msg)
                return {
                    "success": False,
                    "error": "Payment system configuration error. Please contact support."
                }
            
            # Generate unique request ID
            request_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{order_id}"
            
            # Create order data
            order = {
                "partnerCode": self.partner_code,
                "accessKey": self.access_key,
                "requestId": request_id,
                "amount": str(amount),
                "orderId": str(order_id),
                "orderInfo": description,
                "returnUrl": current_app.config['MOMO_REDIRECT_URL'],
                "notifyUrl": current_app.config['MOMO_IPN_URL'],
                "requestType": "captureMoMoWallet",
                "extraData": ""
            }

            # Generate signature
            raw_signature = f"accessKey={order['accessKey']}&amount={order['amount']}&extraData={order['extraData']}&orderId={order['orderId']}&orderInfo={order['orderInfo']}&partnerCode={order['partnerCode']}&requestId={order['requestId']}&returnUrl={order['returnUrl']}"
            order["signature"] = hmac.new(
                self.secret_key.encode(),
                raw_signature.encode(),
                hashlib.sha256
            ).hexdigest()

            try:
                # Send request to MoMo
                response = requests.post(
                    self.payment_url,
                    json=order,
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("errorCode") == 0:
                        return {
                            "success": True,
                            "payment_url": result.get("payUrl"),
                            "request_id": request_id,
                            "message": "Success"
                        }
                    else:
                        error_msg = result.get("localMessage", "Unknown MoMo error")
                        current_app.logger.error(f"MoMo API error: {error_msg}")
                        current_app.logger.error(f"MoMo response: {result}")
                        return {
                            "success": False,
                            "error": f"MoMo error: {error_msg}"
                        }
                
                # Handle non-200 responses
                error_msg = f"MoMo API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('localMessage', '')}"
                    current_app.logger.error("MoMo Error Response:")
                    current_app.logger.error(json.dumps(error_data, indent=2))
                except Exception as json_error:
                    current_app.logger.error(f"Failed to parse error response: {str(json_error)}")
                    current_app.logger.error(f"Raw response: {response.text[:1000]}")
                
                current_app.logger.error("=== MoMo Request Details ===")
                current_app.logger.error(f"Status Code: {response.status_code}")
                current_app.logger.error(f"Request URL: {self.payment_url}")
                current_app.logger.error(f"Request Headers: {json.dumps(dict(response.request.headers), indent=2)}")
                current_app.logger.error(f"Request Data: {json.dumps(order, indent=2)}")
                
                raise ValueError(f"MoMo payment creation failed: {error_msg}")
                
            except requests.exceptions.RequestException as e:
                current_app.logger.error(f"MoMo request failed: {str(e)}")
                current_app.logger.error(f"Request data: {order}")
                raise Exception(f"Failed to connect to MoMo: {str(e)}")
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"MoMo API request error: {str(e)}")
            return {
                "success": False,
                "error": "Failed to connect to MoMo. Please try again."
            }
        except Exception as e:
            current_app.logger.error(f"MoMo order creation error: {str(e)}")
            return {
                "success": False,
                "error": "An error occurred while creating the payment order"
            }

    def verify_callback(self, callback_data: Dict[str, Any]) -> bool:
        """
        Verify the callback data from MoMo
        
        Args:
            callback_data: Callback data received from MoMo
            
        Returns:
            bool: True if verification succeeds, False otherwise
        """
        try:
            # Get signature from callback data
            signature = callback_data.pop('signature', '')
            
            # Create signature string by sorting parameters
            sorted_data = sorted(callback_data.items())
            signature_str = '&'.join(f"{k}={v}" for k, v in sorted_data)
            
            # Calculate signature
            calculated_signature = hmac.new(
                self.secret_key.encode(),
                signature_str.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, calculated_signature)
        except Exception as e:
            current_app.logger.error(f"MoMo callback verification error: {str(e)}")
            return False