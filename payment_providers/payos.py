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
            'PAYOS_SECRET_KEY'  # Updated to use SECRET_KEY instead of CHECKSUM_KEY
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
        self.secret_key = current_app.config['PAYOS_SECRET_KEY']
        self.base_url = "https://api-merchant.payos.vn/v2"  # Changed back to correct endpoint
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
            # Validate order_id format
            try:
                order_id_int = int(order_id)
                if order_id_int <= 0:
                    return {
                        "success": False,
                        "error": "Order ID must be a positive number"
                    }
                if order_id_int > 9007199254740991:  # PayOS max value
                    return {
                        "success": False,
                        "error": "Order ID exceeds maximum allowed value"
                    }
            except ValueError:
                return {
                    "success": False,
                    "error": "Order ID must be a valid number"
                }
                
            request_id = f"REQ_{datetime.now().strftime('%Y%m%d%H%M%S')}_{order_id}"
            
            # Prepare consistent description
            description = f"Payment for order {order_id}"
            cancel_url = f"{current_app.config['BASE_URL']}/payment/payment-result"
            return_url = f"{current_app.config['BASE_URL']}/payment/payment-result"
            
            # Prepare payment data with required fields
            payment_data = {
                "amount": amount,
                "cancelUrl": cancel_url,
                "description": description,
                "orderCode": int(order_id),  # PayOS requires this to be a number
                "returnUrl": return_url
            }

            # Create string for signature in specific order
            # Create dictionary of fields to ensure consistent sorting
            fields = {
                'amount': str(amount),
                'cancelUrl': cancel_url,
                'description': description,
                'orderCode': int(order_id),  # Convert to number for signature generation
                'returnUrl': return_url
            }
            # Sort by keys and concatenate values
            # Build signature string with key=value pairs in alphabetical order, separated by &
            signature_string = '&'.join(f"{key}={str(fields[key])}" for key in sorted(fields))
            
            print("\n🔍 Chi tiết tạo chữ ký:")
            print("1. Các trường theo thứ tự:")
            print(f"   - amount: {amount}")
            print(f"   - cancelUrl: {cancel_url}")
            print(f"   - description: {description}")
            print(f"   - orderCode: {order_id}")
            print(f"   - returnUrl: {return_url}")
            print("2. Chuỗi ký sau khi sắp xếp:", signature_string)
            print("   Thứ tự trường:", ", ".join(sorted(fields.keys())))
            print("3. Secret key:", self.secret_key)
            
            # Generate signature using concatenated string
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                signature_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            print("4. Chữ ký tạo ra:", signature)
            
            # Add signature to payload
            payment_data["signature"] = signature
            
            print("\n🔍 Payload gửi lên PayOS:")
            print(json.dumps(payment_data, indent=2, ensure_ascii=False))

            try:
                # Make API request with updated headers
                # Print request details
                print("\n🔍 Gửi request đến PayOS:")
                print(f"URL: {self.api_endpoint}")
                print("Headers:", {
                    'x-client-id': self.client_id,
                    'x-api-key': self.api_key,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                })

                response = requests.post(
                    self.api_endpoint,
                    json=payment_data,
                    headers={
                        'x-client-id': self.client_id,
                        'x-api-key': self.api_key,
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    timeout=30
                )
            except requests.exceptions.RequestException as e:
                print(f"\n❌ Lỗi kết nối đến PayOS: {str(e)}")
                raise

            # Log response from PayOS
            print("\n🔍 Phản hồi từ PayOS:", response.json())

            if not response.ok:
                current_app.logger.error(f"""
                PayOS API HTTP Error:
                Status Code: {response.status_code}
                Response: {response.text}
                Request Payload: {json.dumps(payment_data, indent=2)}
                """)
                return {
                    "success": False,
                    "error": f"Payment system error (HTTP {response.status_code})"
                }
            
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                current_app.logger.error(f"""
                Failed to parse PayOS response:
                Error: {str(e)}
                Response Text: {response.text}
                Request Payload: {json.dumps(payment_data, indent=2)}
                """)
                return {
                    "success": False,
                    "error": "Invalid response from payment server"
                }

            if not isinstance(result, dict):
                current_app.logger.error(f"""
                Invalid PayOS response format:
                Response: {json.dumps(result, indent=2)}
                Request Payload: {json.dumps(payment_data, indent=2)}
                """)
                return {
                    "success": False,
                    "error": "Invalid response format from payment server"
                }
            
            if result.get('code') == '00' and result.get('data', {}).get('checkoutUrl'):
                return {
                    "success": True,
                    "payment_url": result['data']['checkoutUrl'],
                    "request_id": request_id
                }

            error_msg = result.get('desc', 'Unknown PayOS error')
            error_code = result.get('code', 'UNKNOWN')
            current_app.logger.error(f"""
            PayOS API Error:
            Error Message: {error_msg}
            Response Code: {error_code}
            Full Response: {json.dumps(result, indent=2)}
            Request Payload: {json.dumps(payment_data, indent=2)}
            Signature Details:
            - Fields Order: {", ".join(sorted(fields.keys()))}
            - Raw String: {signature_string}
            - Generated Signature: {signature}
            """)
            return {
                "success": False,
                "error": f"PayOS error ({error_code}): {error_msg}"
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
                self.secret_key.encode(),
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
        using JSON-based signature generation
        """
        try:
            cancel_url = f"{current_app.config['BASE_URL']}/payment/payment-result"
            return_url = f"{current_app.config['BASE_URL']}/payment/payment-result"
            description = f"Payment for order {order_id}"
            
            # Create string for signature in specific order
            # Create dictionary of fields to ensure consistent sorting
            fields = {
                'amount': str(amount),
                'cancelUrl': cancel_url,
                'description': description,
                'orderCode': int(order_id),  # Convert to number for signature generation
                'returnUrl': return_url
            }
            # Sort by keys and concatenate values
            # Build signature string with key=value pairs in alphabetical order, separated by &
            signature_string = '&'.join(f"{key}={str(fields[key])}" for key in sorted(fields))
            
            print("\n🔍 Chi tiết tạo chữ ký:")
            print("1. Các trường theo thứ tự:")
            print(f"   - amount: {amount}")
            print(f"   - cancelUrl: {cancel_url}")
            print(f"   - description: {description}")
            print(f"   - orderCode: {order_id}")
            print(f"   - returnUrl: {return_url}")
            print("2. Chuỗi ký sau khi sắp xếp:", signature_string)
            print("   Thứ tự trường:", ", ".join(sorted(fields.keys())))
            print("3. Secret key:", self.secret_key)
            
            # Generate HMAC SHA256 signature
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                signature_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            print("4. Chữ ký tạo ra:", signature)
            
            return signature
            
        except Exception as e:
            current_app.logger.error(f"Error generating PayOS signature: {str(e)}")
            raise