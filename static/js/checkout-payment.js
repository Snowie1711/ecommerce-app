document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('checkoutForm');
    const orderStatus = document.getElementById('orderStatus');
    const errorDisplay = document.getElementById('errorDisplay');
    const successMessage = document.getElementById('successMessage');
    const placeOrderBtn = document.getElementById('placeOrderBtn');
    const paymentMethodInputs = document.querySelectorAll('input[name="payment_method"]');
    const payosInfo = document.getElementById('payos_info');
    const codInfo = document.getElementById('cod_info');

    // Function to show error message
    function showError(message) {
        errorDisplay.innerHTML = `
            <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4">
                <div class="flex items-center">
                    <div class="mr-2">
                        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"></path>
                        </svg>
                    </div>
                    <div class="flex-1">
                        ${message.split('\n').join('<br>')}
                        ${message.includes('COD') ? '<br><br><strong>Switching to Cash on Delivery...</strong>' : ''}
                    </div>
                </div>
            </div>
        `;
        errorDisplay.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // If error suggests using COD, switch to COD payment method
        if (message.includes('COD')) {
            const codRadio = document.querySelector('input[value="cod"]');
            if (codRadio) {
                codRadio.checked = true;
                codRadio.dispatchEvent(new Event('change'));
            }
        }
    }

    // Function to validate cart
    async function validateCart() {
        try {
            const response = await fetch('/api/cart');
            const data = await response.json();
            
            if (!data.items || data.items.length === 0) {
                throw new Error('Your cart is empty. Please add items before checking out.');
            }
            
            return data;
        } catch (error) {
            console.error('Cart validation error:', error);
            throw error;
        }
    }

    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Clear previous messages
            errorDisplay.innerHTML = '';
            successMessage.classList.add('hidden');
            
            try {
                // Validate cart first
                await validateCart();
                
                // Show loading status
                orderStatus.classList.remove('hidden');
                placeOrderBtn.disabled = true;

                // Get payment method
                const paymentMethod = form.querySelector('input[name="payment_method"]:checked')?.value;
                if (!paymentMethod) {
                    throw new Error('Please select a payment method');
                }

                // Prepare shipping info
                const shippingInfo = {
                    first_name: form.shipping_first_name.value.trim(),
                    last_name: form.shipping_last_name.value.trim(),
                    address: form.shipping_address.value.trim(),
                    city: form.shipping_city.value.trim(),
                    state: form.shipping_state.value.trim(),
                    zip: form.shipping_zip.value.replace(/\D/g, '').padStart(5, '0'),
                    phone: form.shipping_phone.value.replace(/\D/g, '').slice(0, 15)
                };

                // Validate shipping info
                for (const [key, value] of Object.entries(shippingInfo)) {
                    if (!value) {
                        throw new Error(`${key.replace('_', ' ')} is required`);
                    }
                }

                // Validate ZIP code
                if (!/^\d{5}$/.test(shippingInfo.zip)) {
                    throw new Error('ZIP code must be exactly 5 digits');
                }

                // Validate phone number
                if (shippingInfo.phone.length < 10) {
                    throw new Error('Phone number must be at least 10 digits');
                }

                // Submit order
                const response = await fetch('/cart/checkout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-CSRFToken': form.querySelector('input[name="csrf_token"]').value
                    },
                    body: JSON.stringify({
                        shipping_info: shippingInfo,
                        payment_method: paymentMethod
                    })
                });

                const result = await response.json();

                if (!response.ok) {
                    // Handle PayOS errors specially
                    if (result.error && result.error.includes('payment')) {
                        throw new Error(result.error);
                    }
                    throw new Error(result.error || 'Failed to process checkout');
                }

                if (result.requires_payment) {
                    // Redirect to PayOS payment page
                    window.location.href = result.payment_url;
                } else {
                    // Show success message and redirect
                    successMessage.classList.remove('hidden');
                    setTimeout(() => {
                        window.location.href = result.redirect_url;
                    }, 1500);
                }

            } catch (error) {
                console.error('Checkout error:', error);
                
                // Reset UI state
                orderStatus.classList.add('hidden');
                placeOrderBtn.disabled = false;
                
                // Show error message
                showError(error.message);
            }
        });

        // Toggle payment method info sections
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
    }
});