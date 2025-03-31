// Payment form handling with detailed logging
document.addEventListener('DOMContentLoaded', function() {
    console.log('Payment form handler initialized');

    // Get form elements
    const form = document.querySelector('form[action*="add_payment_method"]');
    const paymentProviderSelect = document.getElementById('payment_provider');
    const creditCardFields = document.getElementById('credit_card_fields');
    const zaloPayFields = document.getElementById('zalopay_fields');
    const paymentTokenInput = document.getElementById('payment_token');
    const submitButton = form?.querySelector('button[type="submit"]');

    // Get input fields
    const cardNumber = document.getElementById('card_number');
    const cardholderName = document.getElementById('cardholder_name');
    const expiry = document.getElementById('expiry');
    const cvv = document.getElementById('cvv');
    const zaloPhone = document.getElementById('zalo_phone');
    const cardTypeIcon = document.getElementById('card_type_icon');
    const cardValidationMsg = document.getElementById('card_validation_message');

    // Ensure cardholder name field is read-only
    if (cardholderName) {
        cardholderName.readOnly = true;
        cardholderName.classList.add('bg-gray-50');
    }

    function updatePaymentFields(provider) {
        console.log('Updating fields for provider:', provider);
        creditCardFields?.classList.add('hidden');
        zaloPayFields?.classList.add('hidden');
        
        // Reset all fields
        [cardNumber, expiry, cvv, zaloPhone].forEach(input => {
            if (input) {
                input.required = false;
                input.value = '';
            }
        });

        // Clear cardholder name and validation message
        if (cardholderName) {
            cardholderName.value = '';
        }
        if (cardTypeIcon) {
            cardTypeIcon.innerHTML = '';
        }
        if (cardValidationMsg) {
            cardValidationMsg.classList.add('hidden');
        }

        // Show and require relevant fields
        if (provider === 'credit_card') {
            creditCardFields?.classList.remove('hidden');
            if (cardNumber) cardNumber.required = true;
            if (expiry) expiry.required = true;
            if (cvv) cvv.required = true;
            console.log('Credit card fields activated');
        } else if (provider === 'zalopay') {
            zaloPayFields?.classList.remove('hidden');
            if (zaloPhone) zaloPhone.required = true;
            console.log('ZaloPay fields activated');
        }
    }

    // Card type icons (SVG paths)
    const CARD_ICONS = {
        visa: '<svg class="w-8 h-8" viewBox="0 0 24 24" fill="#1434CB"><path d="M15.4 8.1l-1.7 8H12l1.7-8h1.7zm7.3 5.2l.9-2.6.5 2.6h-1.4zm2.2 2.8h1.6L25 11.3c0-.2-.2-.3-.4-.3h-2.6c-.2 0-.3.1-.4.3l-2.4 6.8h1.8l.3-1h2.2l.4 1zm-5.8-3.7c0-1.7-2.4-1.8-2.3-2.5 0-.2.2-.5.7-.5.6-.1 1.1.1 1.4.2l.3-1.3c-.3-.1-.9-.2-1.5-.2-1.6 0-2.7.8-2.7 2 0 1.4 2.4 1.4 2.4 2.5 0 .3-.3.6-.9.6-.8 0-1.4-.2-1.8-.4l-.3 1.4c.4.2 1.2.3 1.9.3 1.8 0 2.8-.8 2.8-2.1zM7.2 11.3L4.9 18h1.8l.3-1h2.2l.4 1h1.6L9.7 11.3c-.1-.2-.3-.3-.5-.3H7.6c-.2 0-.3.1-.4.3zm1.5 4.3l.9-2.6.5 2.6H8.7z"/></svg>',
        mastercard: '<svg class="w-8 h-8" viewBox="0 0 24 24"><circle cx="8" cy="12" r="6.5" fill="#EB001B" opacity="0.8"/><circle cx="16" cy="12" r="6.5" fill="#F79E1B" opacity="0.8"/></svg>',
        amex: '<svg class="w-8 h-8" viewBox="0 0 24 24" fill="#006FCF"><path d="M21.4 5H2.6C1.7 5 1 5.7 1 6.6v10.8c0 .9.7 1.6 1.6 1.6h18.8c.9 0 1.6-.7 1.6-1.6V6.6c0-.9-.7-1.6-1.6-1.6zm-9.2 10.4h-2.2l-2.3-2.8-2.3 2.8H3.2l3.4-4.1L3.2 7.2h2.2l2.3 2.8 2.3-2.8h2.2l-3.4 4.1 3.4 4.1zm7.6-6.1h-3.7v1.2h3.7v1.6h-3.7v1.2h3.7v1.6l-5.3.1V7.2l5.3-.1v2.2z"/></svg>'
    };

    let validateTimeout;

    cardNumber?.addEventListener('input', function(e) {
        // Format card number
        let value = this.value.replace(/\D/g, '');
        if (value.length > 16) value = value.slice(0, 16);
        let formatted = '';
        for (let i = 0; i < value.length; i++) {
            if (i > 0 && i % 4 === 0) formatted += ' ';
            formatted += value[i];
        }
        this.value = formatted;

        // Clear previous timeout and reset visual indicators
        if (validateTimeout) {
            clearTimeout(validateTimeout);
        }
        cardTypeIcon.innerHTML = '';
        cardValidationMsg.classList.add('hidden');
        cardholderName.value = '';

        // Start validation when we have at least 6 digits (BIN)
        if (value.length >= 6) {
            validateTimeout = setTimeout(async () => {
                try {
                    const response = await fetch('/api/payments/validate-card', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                        },
                        body: JSON.stringify({ card_number: value })
                    });

                    const result = await response.json();

                    if (result.valid) {
                        // Show card type icon
                        if (CARD_ICONS[result.type]) {
                            cardTypeIcon.innerHTML = CARD_ICONS[result.type];
                        }

                        // Set cardholder name
                        if (result.cardholder_name) {
                            cardholderName.value = result.cardholder_name;
                        }

                        // Show success message
                        cardValidationMsg.textContent = `Valid ${result.issuer} card`;
                        cardValidationMsg.classList.remove('hidden', 'text-red-600');
                        cardValidationMsg.classList.add('text-green-600');
                    } else {
                        // Show error message
                        cardValidationMsg.textContent = result.error || 'Invalid card';
                        cardValidationMsg.classList.remove('hidden', 'text-green-600');
                        cardValidationMsg.classList.add('text-red-600');
                        cardholderName.value = ''; // Clear cardholder name
                    }
                } catch (error) {
                    console.error('Card validation error:', error);
                    cardValidationMsg.textContent = 'Error validating card';
                    cardValidationMsg.classList.remove('hidden', 'text-green-600');
                    cardValidationMsg.classList.add('text-red-600');
                    cardholderName.value = ''; // Clear cardholder name
                }
            }, 300); // Reduced timeout for better responsiveness
        }
    });

    expiry?.addEventListener('input', function(e) {
        let value = this.value.replace(/\D/g, '');
        if (value.length > 4) value = value.slice(0, 4);
        if (value.length > 2) {
            value = value.slice(0, 2) + '/' + value.slice(2);
        }
        this.value = value;
    });

    cvv?.addEventListener('input', function(e) {
        let value = this.value.replace(/\D/g, '');
        if (value.length > 4) value = value.slice(0, 4);
        this.value = value;
    });

    zaloPhone?.addEventListener('input', function(e) {
        let value = this.value.replace(/\D/g, '');
        if (value.length > 10) value = value.slice(0, 10);
        this.value = value;
    });

    // Set up payment provider change handler
    if (paymentProviderSelect) {
        updatePaymentFields(paymentProviderSelect.value);
        paymentProviderSelect.addEventListener('change', function() {
            updatePaymentFields(this.value);
        });
    }

    // Form submission handler
    form?.addEventListener('submit', async function(e) {
        e.preventDefault();
        console.log('Form submission started');

        try {
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Processing...';
            }

            // Get and validate payment provider
            const provider = paymentProviderSelect.value;
            if (!provider) {
                throw new Error('Please select a payment method');
            }

            // Handle ZaloPay submission
            if (provider === 'zalopay') {
                const phoneValue = zaloPhone.value;
                if (!phoneValue || phoneValue.length !== 10) {
                    throw new Error('Please enter a valid 10-digit phone number');
                }

                // Create payment request
                const response = await fetch('/create-payment', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                    },
                    body: JSON.stringify({ phone: phoneValue })
                });

                const result = await response.json();
                if (result.success && result.payment_url) {
                    window.location.href = result.payment_url;
                    return;
                } else {
                    throw new Error(result.error || 'Failed to create ZaloPay payment');
                }
            }

            // Handle credit card submission
            if (provider === 'credit_card') {
                const cardNumberValue = cardNumber.value.replace(/\s/g, '');
                const expiryValue = expiry.value;
                const cvvValue = cvv.value;
                const nameValue = cardholderName.value;

                if (!cardNumberValue || !expiryValue || !cvvValue || !nameValue) {
                    throw new Error('Please fill in all credit card fields');
                }

                if (cardNumberValue.length !== 16) {
                    throw new Error('Card number must be 16 digits');
                }

                if (!/^\d{2}\/\d{2}$/.test(expiryValue)) {
                    throw new Error('Invalid expiry date format (MM/YY)');
                }

                if (!/^\d{3,4}$/.test(cvvValue)) {
                    throw new Error('Invalid CVV');
                }

                const paymentData = {
                    number: cardNumberValue,
                    expiry: expiryValue,
                    cvv: cvvValue,
                    name: nameValue
                };

                // Generate token
                const token = await generateToken(provider, paymentData);
                if (!token) {
                    throw new Error('Failed to process payment');
                }
                paymentTokenInput.value = token;

                // Submit form
                form.submit();
            }

        } catch (error) {
            console.error('Payment form error:', error);
            alert(error.message || 'Error processing payment. Please try again.');
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = 'Add Payment Method';
            }
        }
    });

    // Token generation helper
    async function generateToken(provider, data) {
        try {
            const timestamp = Date.now();
            const nonce = Array.from(crypto.getRandomValues(new Uint8Array(16)))
                .map(b => b.toString(16).padStart(2, '0'))
                .join('');
            
            const tokenData = {
                provider,
                timestamp,
                nonce,
                last4: provider === 'credit_card' ? data.number.slice(-4) : data.phone.slice(-4)
            };

            const encoder = new TextEncoder();
            const hashBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(JSON.stringify(data)));
            tokenData.hash = Array.from(new Uint8Array(hashBuffer))
                .map(b => b.toString(16).padStart(2, '0'))
                .join('');

            return btoa(JSON.stringify(tokenData));
        } catch (error) {
            console.error('Token generation failed:', error);
            throw error;
        }
    }
});