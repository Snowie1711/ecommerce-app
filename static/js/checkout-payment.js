function validateZipCode(input) {
    const value = input.value.replace(/\D/g, '').slice(0, 5).padStart(5, '0');
    input.value = value;
    const isValid = /^\d{5}$/.test(value);
    input.classList.toggle('border-red-500', !isValid);
    return isValid;
}

function validatePhoneNumber(input) {
    const value = input.value.replace(/\D/g, '');
    input.value = value;
    const isValid = value.length >= 10;
    input.classList.toggle('border-red-500', !isValid);
    return isValid;
}

function validateZipCode(input) {
    // Remove non-digits and limit to 5 characters
    const value = input.value.replace(/\D/g, '').slice(0, 5);
    
    // Log validation details
    console.log('ZIP Code Validation:', {
        original: input.value,
        cleaned: value,
        length: value.length,
        isValid: /^\d{5}$/.test(value)
    });

    // Only pad if we have some digits
    const formatted = value ? value.padStart(5, '0') : value;
    
    // Update input value
    input.value = formatted;
    
    // Check validity
    const isValid = /^\d{5}$/.test(formatted);
    input.classList.toggle('border-red-500', !isValid);
    
    if (!isValid) {
        input.setAttribute('title', 'ZIP code must be exactly 5 digits');
    } else {
        input.removeAttribute('title');
    }
    
    return isValid;
}

function validatePhoneNumber(input) {
    const value = input.value.replace(/\D/g, '');
    input.value = value;
    const isValid = value.length >= 10;
    input.classList.toggle('border-red-500', !isValid);
    return isValid;
}

function validateForm(fields) {
    for (const [key, field] of Object.entries(fields)) {
        if (!field || !field.value.trim()) {
            throw new Error(`${key} is required`);
        }
        if (field.classList.contains('border-red-500')) {
            throw new Error(`Please fix the validation errors before submitting`);
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('checkoutForm');
    const fields = {
        firstName: document.getElementById('shipping_first_name'),
        lastName: document.getElementById('shipping_last_name'),
        address: document.getElementById('shipping_address'),
        city: document.getElementById('shipping_city'),
        state: document.getElementById('shipping_state'),
        zip: document.getElementById('shipping_zip'),
        phone: document.getElementById('shipping_phone')
    };

    // Add validation listeners
    if (fields.zip) {
        fields.zip.addEventListener('blur', () => validateZipCode(fields.zip));
        fields.zip.addEventListener('input', () => fields.zip.classList.remove('border-red-500'));
    }

    if (fields.phone) {
        fields.phone.addEventListener('blur', () => validatePhoneNumber(fields.phone));
        fields.phone.addEventListener('input', () => fields.phone.classList.remove('border-red-500'));
    }

    // Add blur validation for required fields
    for (const [key, field] of Object.entries(fields)) {
        if (field) {
            field.addEventListener('blur', () => {
                field.classList.toggle('border-red-500', !field.value.trim());
            });
            field.addEventListener('input', () => field.classList.remove('border-red-500'));
        }
    }

    // Get status elements
    const orderStatus = document.getElementById('orderStatus');
    const errorDisplay = document.getElementById('errorDisplay');
    const successMessage = document.getElementById('successMessage');
    const placeOrderBtn = document.getElementById('placeOrderBtn');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Clear previous messages
        errorDisplay.innerHTML = '';
        successMessage.classList.add('hidden');
        
        // Show loading status
        orderStatus.classList.remove('hidden');
        placeOrderBtn.disabled = true;

        try {
            // Get payment method
            const paymentMethod = form.querySelector('input[name="payment_method"]:checked')?.value;
            if (!paymentMethod) {
                throw new Error('Please select a payment method');
            }

            // Validate all form fields
            validateForm(fields);

            // Prepare shipping info with formatted values
            const requestData = {
                shipping_info: {
                    first_name: fields.firstName.value.trim(),
                    last_name: fields.lastName.value.trim(),
                    address: fields.address.value.trim(),
                    city: fields.city.value.trim(),
                    state: fields.state.value.trim(),
                    zip: fields.zip.value.replace(/\D/g, '').padStart(5, '0'),
                    phone: fields.phone.value.replace(/\D/g, '').slice(0, 15)
                },
                payment_method: paymentMethod,
                cart_total: document.getElementById('cart_total')?.value
            };

            console.log('Submitting checkout with data:', requestData);

            // Submit order
            const response = await fetch('/cart/checkout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Failed to create order');
            }

            if (result.requires_payment) {
                // Redirect to payment page
                window.location.href = result.payment_url;
            } else {
                // Show success message
                successMessage.classList.remove('hidden');
                setTimeout(() => {
                    window.location.href = result.redirect_url;
                }, 1500);
            }

        } catch (error) {
            console.error('Checkout error:', error);
            orderStatus.classList.add('hidden');
            placeOrderBtn.disabled = false;

            // Display error message
            errorDisplay.innerHTML = `
                <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
                    <div class="flex items-center">
                        <div class="mr-2">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"></path>
                            </svg>
                        </div>
                        <div class="flex-1">
                            ${error.message.split('\n').join('<br>')}
                        </div>
                        <button onclick="this.parentElement.parentElement.remove()" class="ml-4">
                            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            `;
            
            // Scroll to error message
            errorDisplay.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        try {
            const formData = new FormData(form);
            const paymentMethod = formData.get('payment_method');
            if (!paymentMethod) {
                throw new Error('Please select a payment method');
            }

            // Get form values
            const zipInput = document.getElementById('shipping_zip');
            const zipValue = zipInput ? zipInput.value : '';
            
            // Validate ZIP code format (exactly 5 digits)
            if (!zipValue) {
                throw new Error('ZIP code is required');
            }

            // Ensure ZIP code is exactly 5 digits
            const formattedZip = zipValue.replace(/\D/g, '').slice(0, 5).padStart(5, '0');
            if (formattedZip.length !== 5) {
                throw new Error('ZIP code must be exactly 5 digits');
            }

            // Update the input value to show the formatted ZIP
            if (zipInput) {
                zipInput.value = formattedZip;
            }

            // Get and validate phone number
            const phoneInput = document.getElementById('shipping_phone');
            const phoneValue = phoneInput ? phoneInput.value.replace(/\D/g, '') : '';
            
            if (!phoneValue || phoneValue.length < 10) {
                throw new Error('Phone number must be at least 10 digits');
            }

            // Format phone number to keep only digits
            const formattedPhone = phoneValue.slice(0, 15); // Limit to 15 digits max

            if (phoneInput) {
                phoneInput.value = formattedPhone;
            }

            // Prepare request data with validated and formatted values
            const requestData = {
                shipping_info: {
                    first_name: document.getElementById('shipping_first_name').value.trim(),
                    last_name: document.getElementById('shipping_last_name').value.trim(),
                    address: document.getElementById('shipping_address').value.trim(),
                    city: document.getElementById('shipping_city').value.trim(),
                    state: document.getElementById('shipping_state').value.trim(),
                    zip: formattedZip,
                    phone: formattedPhone
                },
                payment_method: paymentMethod,
                cart_total: document.getElementById('cart_total').value
            };

            // Log the formatted data for debugging
            console.log('Sending checkout request with data:', requestData);

            // Validate shipping info
            const requiredFields = ['first_name', 'last_name', 'address', 'city', 'state', 'zip', 'phone'];
            const missingFields = requiredFields.filter(field => !requestData.shipping_info[field]);
            if (missingFields.length > 0) {
                throw new Error(`Missing required fields: ${missingFields.join(', ')}`);
            }

            // Create order first
            const orderResponse = await fetch('/cart/checkout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRFToken': formData.get('csrf_token')
                },
                body: JSON.stringify(requestData)
            });

            // Always try to parse the response body
            const orderData = await orderResponse.json().catch(e => ({
                error: 'Failed to parse server response',
                details: e.message
            }));
            
            if (!orderResponse.ok) {
                const error = new Error(orderData.error || 'Failed to create order');
                error.response = orderData;
                throw error;
            }
            
            if (paymentMethod === 'cod') {
                // For COD, redirect to success page
                window.location.href = `/orders/${orderData.order_id}`;
                return;
            }
            
            // For PayOS, create payment
            const paymentResponse = await fetch('/payment/create-payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': formData.get('csrf_token')
                },
                body: JSON.stringify({
                    order_id: orderData.order_id,
                    amount: formData.get('cart_total')
                })
            });

            // Parse payment response
            const paymentData = await paymentResponse.json().catch(e => ({
                error: 'Failed to parse payment response',
                details: e.message
            }));

            if (!paymentResponse.ok) {
                const error = new Error(paymentData.error || paymentData.message || 'Failed to create payment');
                error.response = paymentData;
                error.paymentDetails = {
                    status: paymentResponse.status,
                    statusText: paymentResponse.statusText,
                    requestId: paymentData.requestId || 'unknown'
                };
                throw error;
            }

            if (!paymentData) {
                throw new Error('No response data received from payment server');
            }

            if (paymentData.success && paymentData.payment_url) {
                // Redirect to PayOS payment page
                window.location.href = paymentData.payment_url;
            } else {
                const errorMessage = paymentData.error || paymentData.message || 'Payment initialization failed';
                throw new Error(errorMessage);
            }

        } catch (error) {
            console.error('Payment error:', error);
            orderStatus.classList.add('hidden');
            placeOrderBtn.disabled = false;

            // Clear previous error messages
            errorDisplay.innerHTML = '';
            
            // Handle error response
            let errorMessage;
            
            if (error.name === 'TypeError' && error.message.includes('orderResponse')) {
                // Handle client-side validation errors
                errorMessage = error.message;
            } else {
                try {
                    const errorData = error.response ? await error.response.json() : {};
                    errorMessage = errorData.error || error.message || 'An unexpected error occurred';
                    
                    if (errorData.context) {
                        console.error('Error context:', errorData.context);
                        if (errorData.status === 'validation_error') {
                            // Add validation details to the error message
                            const validation = errorData.context.validation_state;
                            if (validation) {
                                const issues = [];
                                if (!validation.shipping_info_present) issues.push('Shipping information is missing');
                                if (!validation.shipping_info_valid) issues.push('Invalid shipping information format');
                                if (!validation.payment_method_valid) issues.push('Invalid payment method');
                                
                                if (issues.length > 0) {
                                    errorMessage += '\n\nValidation issues:\n• ' + issues.join('\n• ');
                                }
                            }
                            errorMessage += '\n\nPlease check your input and try again.';
                        }
                    }
                } catch (parseError) {
                    console.error('Error parsing server response:', parseError);
                    errorMessage = error.message || 'Failed to process server response';
                }
            }
            
            console.error('Checkout error:', { message: errorMessage, originalError: error });

            // Display error message using template
            errorDisplay.innerHTML = `
                <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
                    <div class="flex items-center">
                        <div class="mr-2">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"></path>
                            </svg>
                        </div>
                        <div class="flex-1">
                            ${errorMessage.split('\n').join('<br>')}
                        </div>
                        <button onclick="this.parentElement.parentElement.remove()" class="ml-4">
                            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            `;
            
            // Scroll to error message
            errorDisplay.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });
});