document.addEventListener('DOMContentLoaded', function() {
    const checkoutForm = document.getElementById('checkoutForm');
    const placeOrderBtn = document.getElementById('placeOrderBtn');
    const orderStatus = document.getElementById('orderStatus');
    const errorDisplay = document.getElementById('errorDisplay');
    const successMessage = document.getElementById('successMessage');
    const DEBUG_MODE = true;

    function logDebug(message) {
        if (DEBUG_MODE) {
            console.log(`[DEBUG] ${message}`);
        }
    }

    function showError(message) {
        errorDisplay.innerHTML = `
            <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
                <strong class="font-bold">Error!</strong>
                <p class="block sm:inline">${message}</p>
            </div>
        `;
        errorDisplay.classList.remove('hidden');
        orderStatus.classList.add('hidden');
    }

    function validateCart() {
        return new Promise((resolve, reject) => {
            fetch('/api/cart')
                .then(response => response.json())
                .then(data => {
                    if (!data.items || data.items.length === 0) {
                        reject(new Error('Your cart is empty'));
                        return;
                    }
                    resolve(data);
                })
                .catch(error => {
                    reject(error);
                });
        });
    }

    if (checkoutForm) {
        checkoutForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Clear previous messages
            errorDisplay.innerHTML = '';
            successMessage.classList.add('hidden');
            
            try {
                // Show processing status
                orderStatus.classList.remove('hidden');
                placeOrderBtn.disabled = true;

                // Validate cart first
                await validateCart();

                // Get form data
                const formData = new FormData(checkoutForm);
                const jsonData = {
                    shipping_info: {
                        first_name: formData.get('shipping_first_name'),
                        last_name: formData.get('shipping_last_name'),
                        address: formData.get('shipping_address'),
                        address2: formData.get('shipping_address2'),
                        city: formData.get('shipping_city'),
                        state: formData.get('shipping_state'),
                        zip: formData.get('shipping_zip'),
                        phone: formData.get('shipping_phone')
                    },
                    payment_method: formData.get('payment_method')
                };

                // Send request
                const response = await fetch('/cart/checkout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-CSRFToken': formData.get('csrf_token')
                    },
                    body: JSON.stringify(jsonData)
                });

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || 'Error processing checkout');
                }

                // Handle successful response
                if (result.success) {
                    if (result.requires_payment && result.payment_url) {
                        // Redirect to payment page for PayOS
                        window.location.href = result.payment_url;
                    } else {
                        // Show success message for COD
                        successMessage.classList.remove('hidden');
                        orderStatus.classList.add('hidden');
                        
                        // Redirect to order history after a delay
                        setTimeout(() => {
                            window.location.href = result.redirect_url;
                        }, 2000);
                    }
                }

            } catch (error) {
                logDebug(`Checkout error: ${error.message}`);
                showError(error.message);
                placeOrderBtn.disabled = false;
            }
        });
    }

    // Update payment method info display
    const paymentMethodInputs = document.querySelectorAll('input[name="payment_method"]');
    const payosInfo = document.getElementById('payos_info');
    const codInfo = document.getElementById('cod_info');

    paymentMethodInputs.forEach(input => {
        input.addEventListener('change', function() {
            if (this.value === 'payos') {
                payosInfo.classList.remove('hidden');
                codInfo.classList.add('hidden');
            } else {
                payosInfo.classList.add('hidden');
                codInfo.classList.remove('hidden');
            }
        });
    });
});
