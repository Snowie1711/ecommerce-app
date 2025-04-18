document.addEventListener('DOMContentLoaded', function() {
    // Update cart badge when page loads
    updateCartBadge();

    // Function to update cart badge and validate cart
    function updateCartBadge() {
        fetch('/api/cart')
            .then(response => response.json())
            .then(data => {
                console.log('Cart data:', data);
                const cartBadge = document.getElementById('cart-badge');
                if (cartBadge) {
                    const itemCount = data.items ? data.items.reduce((total, item) => total + item.quantity, 0) : 0;
                    cartBadge.textContent = itemCount;
                    cartBadge.style.display = itemCount > 0 ? 'flex' : 'none';
                }

                // Validate cart contents for checkout
                const checkoutBtn = document.getElementById('checkoutBtn');
                if (checkoutBtn) {
                    const hasItems = data.items && data.items.length > 0;
                    checkoutBtn.disabled = !hasItems;
                    checkoutBtn.title = hasItems ? '' : 'Your cart is empty';
                }
            })
            .catch(error => console.error('Error updating cart:', error));
    }

    // Function to validate cart before checkout
    async function validateCart() {
        try {
            const response = await fetch('/api/cart');
            const data = await response.json();
            
            console.log('Validating cart:', data);
            
            if (!data.items || data.items.length === 0) {
                throw new Error('Your cart is empty');
            }
            
            return data;
        } catch (error) {
            console.error('Cart validation error:', error);
            throw error;
        }
    }

    // Listen for custom event when cart is updated
    document.addEventListener('cartUpdated', function() {
        updateCartBadge();
    });

    // Handle checkout button click
    document.getElementById('checkoutBtn')?.addEventListener('click', async function(e) {
        e.preventDefault();
        
        try {
            await validateCart();
            window.location.href = this.getAttribute('href');
        } catch (error) {
            alert('Please add items to your cart before proceeding to checkout.');
            return false;
        }
    });

    // Handle add to cart forms
    document.querySelectorAll('form').forEach(form => {
        const formAction = form.getAttribute('action') || '';
        if (formAction.includes('/cart/add/')) {
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formAction = form.getAttribute('action') || '';
                const productId = formAction.split('/cart/add/')[1];
                const quantity = form.querySelector('select[name="quantity"]')?.value || 1;
                const size = form.querySelector('select[name="size"]')?.value;
                const colorInput = form.querySelector('input[name="color_id"]:checked');
                const csrfToken = form.querySelector('input[name="csrf_token"]').value;

                // Validation for required fields
                const sizeRequired = form.querySelector('#size') && !form.querySelector('#size').disabled;
                const colorRequired = form.querySelectorAll('input[name="color_id"]').length > 0;

                if (sizeRequired && !size) {
                    alert('Please select a size');
                    return;
                }

                if (colorRequired && !colorInput) {
                    alert('Please select a color');
                    return;
                }

                try {
                    const response = await fetch(`/api/cart/add/${productId}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': csrfToken
                        },
                        body: JSON.stringify({
                            quantity: parseInt(quantity),
                            size: size || null,
                            color_id: colorInput ? parseInt(colorInput.value) : null,
                            csrf_token: csrfToken
                        })
                    });

                    if (!response.ok) {
                        const data = await response.json();
                        const errorMessage = data.error || 'Error adding item to cart';
                        showErrorMessage(errorMessage);
                        throw new Error(errorMessage);
                    }

                    // Show success message
                    showSuccessMessage('Item added to cart successfully!');

                    // Update cart badge
                    document.dispatchEvent(new CustomEvent('cartUpdated'));

                } catch (error) {
                    // Extract proper error message
                    let errorMessage;
                    if (error instanceof Error) {
                        errorMessage = error.message;
                    } else if (typeof error === 'string') {
                        errorMessage = error;
                    } else if (error && typeof error === 'object') {
                        errorMessage = error.error || error.message || JSON.stringify(error);
                    } else {
                        errorMessage = 'Failed to add item to cart';
                    }
                    
                    showErrorMessage(errorMessage);
                }
            });
        } else if ((form.getAttribute('action') || '').includes('/cart/')) {
            // For other cart forms (remove, update) - keep original behavior
            form.addEventListener('submit', function() {
                setTimeout(() => {
                    document.dispatchEvent(new CustomEvent('cartUpdated'));
                }, 100);
            });
        }
    });

    // Format number with commas and VND symbol - cải thiện để định dạng đúng
    function formatPrice(number) {
        // Đảm bảo number là một số hợp lệ
        const value = typeof number === 'string' ? parseFloat(number.replace(/[^\d.-]/g, '')) : parseFloat(number);
        
        if (isNaN(value)) {
            console.warn('Invalid price value:', number);
            return '0₫';
        }
        
        // Log để debug
        console.log(`Formatting price: ${number} → ${value}`);
        
        try {
            // Sử dụng Intl.NumberFormat để định dạng đúng tiền tệ Việt Nam 
            return new Intl.NumberFormat('vi-VN', {
                style: 'currency',
                currency: 'VND',
                maximumFractionDigits: 0,
                currencyDisplay: 'symbol'
            }).format(value).replace('VND', '').trim() + '₫';
        } catch (error) {
            console.error('Error formatting price:', error);
            // Fallback formatting
            return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") + '₫';
        }
    }

    // Update cart prices
    function updateCartPrices(data) {
        try {
            // Update cart summary totals
            const summaryContainer = document.querySelector('.space-y-4.mb-6');
            if (summaryContainer) {
                // Update subtotal
                const summarySubtotal = summaryContainer.querySelector('.flex.justify-between:first-child .font-semibold');
                if (summarySubtotal && data.subtotal) {
                    summarySubtotal.textContent = formatPrice(data.subtotal);
                }

                // Update total
                const summaryTotal = summaryContainer.querySelector('.border-t.border-gray-200 .text-lg.font-bold:last-child');
                if (summaryTotal && data.total) {
                    summaryTotal.textContent = formatPrice(data.total);
                }

                // Update shipping message if needed
                const shippingMessage = summaryContainer.querySelector('.text-sm.text-gray-500.mt-2');
                if (shippingMessage && typeof data.subtotal === 'number') {
                    const remaining = 1000000 - data.subtotal;
                    if (remaining > 0) {
                        shippingMessage.textContent = `Add ${formatPrice(remaining)} more to get free shipping!`;
                    } else {
                        shippingMessage.textContent = 'Eligible for free shipping!';
                    }
                }
            }
        } catch (error) {
            console.error('Error updating cart prices:', error);
        }
    }

    // Handle quantity select changes
    document.querySelectorAll('.quantity-select').forEach(select => {
        if (!select.disabled) {
            // Store initial value
            select.dataset.originalValue = select.value;
            
            select.addEventListener('change', async function(e) {
                e.preventDefault();
                
                const itemId = this.dataset.itemId;
                const quantity = parseInt(this.value, 10);
                const originalValue = parseInt(this.dataset.originalValue, 10);
                
                if (!itemId) {
                    console.error('No item ID found');
                    return;
                }

                try {
                    this.disabled = true;
                    
                    // Get CSRF token properly
                    const csrfTokenInput = document.querySelector('input[name="csrf_token"]');
                    if (!csrfTokenInput || !csrfTokenInput.value) {
                        throw new Error('CSRF token not found. Please refresh the page.');
                    }
                    const csrfToken = csrfTokenInput.value;

                    // Show a temporary loading indicator
                    const loadingToast = showLoadingMessage('Updating cart...');

                    // Log request details for debugging
                    console.log(`Updating item ${itemId} quantity to ${quantity}`);

                    // Fixed: Add the missing METHOD parameter to fetch request
                    const response = await fetch(`/cart/update/${itemId}`, {
                        method: 'POST', // Added missing method
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': csrfToken
                        },
                        body: JSON.stringify({
                            quantity: quantity,
                            csrf_token: csrfToken
                        })
                    });

                    // Debug logging for response details
                    console.log('Response status:', response.status, 'Status text:', response.statusText);
                    console.log('Content-Type:', response.headers.get('content-type'));

                    // Remove loading indicator
                    if (loadingToast) loadingToast.remove();

                    // Check if response is JSON before attempting to parse
                    const contentType = response.headers.get('content-type');
                    let data;
                    if (contentType && contentType.includes('application/json')) {
                        // Handle JSON responses
                        data = await response.json();
                        console.log('Response data:', data);

                        // Check for error in response data even if status is 200
                        if (!response.ok || data.error || data.success === false) {
                            const errorMsg = data.error || data.message || `Server error: ${response.status}`;
                            console.error('Error from server:', errorMsg);
                            showErrorMessage(errorMsg);
                            throw new Error(errorMsg);
                        }

                        // Handle success message if provided
                        if (data.message) {
                            showSuccessMessage(data.message);
                        } else {
                            showSuccessMessage('Cart updated successfully');
                        }

                        // Always fetch fresh cart data after any update
                        try {
                            console.log('Fetching complete cart data for UI refresh...');
                            const cartResponse = await fetch('/api/cart');
                            if (!cartResponse.ok) {
                                throw new Error('Failed to fetch latest cart data');
                            }
                            const freshCartData = await cartResponse.json();
                            console.log('Fresh cart data received:', freshCartData);
                            
                            // Use the enhanced comprehensive UI update function
                            updateUIFromCartData(freshCartData, true);
                        } catch (cartError) {
                            console.error('Error refreshing cart data:', cartError);
                            // Fallback to using the initial response data if available
                            if (data.subtotal !== undefined || data.total !== undefined) {
                                updateCartPrices(data);
                            }
                        }

                        // Update stored value after successful update
                        this.dataset.originalValue = quantity.toString();

                        // Update cart badge and other components
                        document.dispatchEvent(new CustomEvent('cartUpdated'));
                    } else {
                        // Non-JSON response, log the actual content for debugging
                        const responseText = await response.text();
                        console.error('Non-JSON response:', responseText);
                        throw new Error('Server returned non-JSON response. Please try again.');
                    }
                } catch (error) {
                    console.error('Error updating cart:', error);
                    // Revert to previous value on error
                    const originalValue = this.dataset.originalValue || '1';
                    this.value = originalValue;

                    // Extract proper error message
                    let errorMessage;
                    if (error instanceof Error) {
                        errorMessage = error.message;
                    } else if (typeof error === 'string') {
                        errorMessage = error;
                    } else if (error && typeof error === 'object') {
                        errorMessage = error.error || error.message || JSON.stringify(error);
                    } else {
                        errorMessage = 'Failed to update cart';
                    }
                    
                    showErrorMessage(errorMessage);
                } finally {
                    this.disabled = false;
                }
            });
        }
    });

    // Function to update a specific item's subtotal
    function updateItemSubtotal(itemId, quantity) {
        // Find the item row in the cart
        const itemRow = document.querySelector(`.cart-item[data-item-id="${itemId}"]`) || 
                        document.querySelector(`[data-item-id="${itemId}"]`);
        if (!itemRow) {
            console.warn(`Item row not found for item ID: ${itemId}`);
            return;
        }

        // Find the price element
        let priceElement = itemRow.querySelector('.item-price') || 
                          itemRow.querySelector('.text-gray-900:not(.item-subtotal)');
        if (!priceElement) {
            console.warn('Price element not found for item');
            return;
        }

        // Parse the price (remove currency symbol and commas)
        const priceText = priceElement.textContent.trim();
        // Improved price parsing - handle ₫ symbol and remove all non-numeric characters except decimal point
        const price = parseFloat(priceText.replace(/[^\d.]/g, ''));
        
        // Debug log for price parsing
        console.log(`Parsing price from "${priceText}" → ${price}`);
        
        if (isNaN(price)) {
            console.warn(`Could not parse price from: ${priceText}`);
            return;
        }

        // Calculate new subtotal
        const subtotal = price * quantity;
        console.log(`Calculated subtotal: ${price} × ${quantity} = ${subtotal}`);

        // Find subtotal element
        const subtotalElement = itemRow.querySelector('.item-subtotal') || 
                              itemRow.querySelector('.text-gray-900.font-semibold.w-24.text-right');
        if (subtotalElement) {
            subtotalElement.textContent = formatPrice(subtotal);
            console.log(`Updated subtotal for item ${itemId}: ${formatPrice(subtotal)}`);
        } else {
            console.warn('Subtotal element not found');
        }
    }

    // Function to update all cart items based on complete cart data
    function updateAllCartItems(cartData) {
        if (!cartData.items || !Array.isArray(cartData.items)) {
            console.warn('No items found in cart data');
            return;
        }

        console.log('Updating all cart items with data:', cartData.items);

        // Loop through all items in cart
        cartData.items.forEach(item => {
            if (!item.product) {
                console.warn(`Item ${item.id} has no product data`);
                return;
            }

            // Parse price and quantity as numbers to ensure correct calculations
            const price = parseFloat(item.product.price);
            const quantity = parseInt(item.quantity, 10);
            
            // Calculate subtotal correctly and log details for debugging
            const subtotal = price * quantity;
            console.log(`Item ${item.id}: ${item.product.name || 'Unknown'} - Price: ${price}, Qty: ${quantity}, Subtotal: ${subtotal}`);
            
            // Find the item row by its itemId
            const itemRow = document.querySelector(`.cart-item[data-item-id="${item.id}"]`) || 
                           document.querySelector(`[data-item-id="${item.id}"]`);
            if (itemRow) {
                // Find price element
                const priceElement = itemRow.querySelector('.item-price') || 
                                   itemRow.querySelector('.text-gray-900:not(.font-semibold)');

                // Find subtotal element
                const subtotalElement = itemRow.querySelector('.item-subtotal') || 
                                      itemRow.querySelector('.text-gray-900.font-semibold.w-24.text-right');

                if (priceElement) {
                    priceElement.textContent = formatPrice(price);
                    console.log(`Updated price display for item ${item.id}: ${formatPrice(price)}`);
                }

                if (subtotalElement) {
                    subtotalElement.textContent = formatPrice(subtotal);
                    console.log(`Updated subtotal for item ${item.id}: ${formatPrice(subtotal)}`);
                } else {
                    console.warn(`Subtotal element not found for item ${item.id}`);
                }
            } else {
                console.warn(`Item row not found for item ID: ${item.id}`);
            }
        });

        // Always update the cart summary after updating items
        updateCartSummary(cartData);
    }

    // Function to update available quantities based on size/color selection
    async function updateQuantityOptions() {
        const sizeSelect = document.getElementById('size');
        const selectedSize = sizeSelect ? sizeSelect.value : null;
        const selectedColor = document.querySelector('input[name="color_id"]:checked');
        const quantitySelect = document.querySelector('select[name="quantity"]');
        const currentValue = quantitySelect ? quantitySelect.value : 1;

        if (!quantitySelect) return;

        // Get the product ID from the form action
        const form = quantitySelect.closest('form');
        if (!form || !form.action) return;
        const productId = form.action.split('/cart/add/')[1];
        if (!productId) return;

        try {
            // Fetch available stock for selected variant
            const response = await fetch(`/api/products/${productId}/stock?` + new URLSearchParams({
                size: selectedSize || '',
                color_id: selectedColor ? selectedColor.value : ''
            }));
            const data = await response.json();
            if (!response.ok) {
                throw new Error('Failed to fetch stock information');
            }
            const stock = data.stock || 0;

            // Update quantity options
            quantitySelect.innerHTML = '';
            const maxQuantity = Math.min(10, stock);
            for (let i = 1; i <= maxQuantity; i++) {
                const option = document.createElement('option');
                option.value = i;
                option.textContent = i;
                if (i === parseInt(currentValue)) {
                    option.selected = true;
                }
                quantitySelect.appendChild(option);
            }

            // If current value is greater than available stock, reset to 1
            if (parseInt(currentValue) > maxQuantity) {
                quantitySelect.value = '1';
            }

            // Disable select if no stock
            quantitySelect.disabled = stock === 0;

            // Store current value for rollback
            quantitySelect.dataset.originalValue = quantitySelect.value;
        } catch (error) {
            console.error('Error updating quantity options:', error);
            // Keep the current options on error
            if (quantitySelect.options.length === 0) {
                const option = document.createElement('option');
                option.value = '1';
                option.textContent = '1';
                quantitySelect.appendChild(option);
            }
        }
    }

    // Function to add item to cart
    function addToCart(productId, quantity = 1, size = null, colorId = null) {
        fetch(`/api/cart/add/${productId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ quantity, size, color_id: colorId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Item added to cart:', data);
                document.dispatchEvent(new CustomEvent('cartUpdated'));
            } else {
                console.error('Error adding item to cart:', data.error);
            }
        })
        .catch(error => console.error('Error adding item to cart:', error));
    }

    // Function to update cart item quantity
    async function updateCartItemQuantity(itemId, quantity) {
        try {
            console.log('Updating cart item:', { itemId, quantity });

            // Simplified CSRF token extraction - get from any form or dedicated hidden input
            const csrfTokenInput = document.querySelector('input[name="csrf_token"]');
            if (!csrfTokenInput || !csrfTokenInput.value) {
                const errorMsg = 'CSRF token not found. Please refresh the page and try again.';
                showErrorMessage(errorMsg);
                throw new Error(errorMsg);
            }
            const csrfToken = csrfTokenInput.value;
            console.log('Found CSRF token for request');

            // Send as JSON with proper CSRF token in header AND body for double protection
            const response = await fetch(`/cart/update/${itemId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-CSRF-Token': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    quantity: quantity,
                    csrf_token: csrfToken
                })
            });

            console.log('Response status:', response.status, 'Status text:', response.statusText);

            // Check HTTP status first
            if (!response.ok) {
                let errorMessage;
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    const errorData = await response.json();
                    console.error('Server error response:', errorData);
                    errorMessage = errorData.error || errorData.message || `Server error: ${response.status} - ${response.statusText}`;
                } else {
                    const text = await response.text();
                    console.error('Server error (non-JSON):', text);
                    errorMessage = `Server error: ${response.status} - ${response.statusText}`;
                }
                showErrorMessage(errorMessage);
                throw new Error(errorMessage);
            }

            // Try to parse JSON response
            let data;
            const contentType = response.headers.get('content-type');
            console.log('Response content type:', contentType);
            if (contentType && contentType.includes('application/json')) {
                try {
                    data = await response.json();
                    console.log('Parsed response data:', data);

                    // Check for error in JSON response even if status code was 200
                    if (data.error) {
                        const errorMsg = typeof data.error === 'string' ? data.error : JSON.stringify(data.error);
                        showErrorMessage(errorMsg);
                        throw new Error(errorMsg);
                    }

                    // Check if success field is false
                    if (data.success === false) {
                        const errorMsg = data.message || 'Operation failed';
                        showErrorMessage(errorMsg);
                        throw new Error(errorMsg);
                    }
                } catch (e) {
                    console.error('JSON parse error:', e);
                    showErrorMessage('Failed to parse server response');
                    throw new Error('JSON parsing error: ' + e.message);
                }
            } else {
                console.log('Response is not JSON, refreshing page');
                showErrorMessage('Unexpected response from server. Refreshing page...');
                setTimeout(() => window.location.reload(), 2000);
                return;
            }

            // Show success message
            showSuccessMessage('Cart updated successfully');

            // Log successful response
            console.log('Cart update successful:', data);

            // Update prices in the UI
            if (data.subtotal !== undefined || data.total !== undefined) {
                updateCartPrices(data);
            } else {
                console.warn('Missing price information in response');
            }

            // Update previous value after successful update
            const select = document.querySelector(`.quantity-select[data-item-id="${itemId}"]`);
            if (select) {
                select.dataset.originalValue = quantity.toString();
            }

            // Notify other components
            document.dispatchEvent(new CustomEvent('cartUpdated'));
            return data;
        } catch (error) {
            console.error('Error in updateCartItemQuantity:', error);
            showErrorMessage(error);

            // Make sure error is displayed as a string rather than [object Object]
            if (error instanceof Error) {
                console.error('Error details:', error.message);
                throw error;
            } else if (typeof error === 'string') {
                throw new Error(error);
            } else if (error && typeof error === 'object') {
                console.error('Error object:', JSON.stringify(error));
                throw new Error(JSON.stringify(error));
            } else {
                throw error;
            }
        }
    }

    // Helper function to show error messages
    function showErrorMessage(message) {
        console.error('Error message:', message);
        const messageDiv = document.createElement('div');
        messageDiv.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded shadow-lg z-50';
        messageDiv.textContent = message;
        document.body.appendChild(messageDiv);
        
        // Remove message after 5 seconds
        setTimeout(() => {
            messageDiv.classList.add('opacity-0', 'transition-opacity', 'duration-500');
            setTimeout(() => messageDiv.remove(), 500);
        }, 5000);
    }

    // Helper function to show success messages
    function showSuccessMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded shadow-lg z-50';
        messageDiv.textContent = message;
        document.body.appendChild(messageDiv);
        
        // Remove message after 3 seconds with fade out
        setTimeout(() => {
            messageDiv.classList.add('opacity-0', 'transition-opacity', 'duration-500');
            setTimeout(() => messageDiv.remove(), 500);
        }, 3000);
    }

    // Helper function to show loading messages
    function showLoadingMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'fixed top-4 right-4 bg-blue-500 text-white px-6 py-3 rounded shadow-lg z-50 flex items-center';
        
        // Add spinner
        const spinner = document.createElement('div');
        spinner.className = 'animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-3';
        messageDiv.appendChild(spinner);
        
        // Add text message
        const textSpan = document.createElement('span');
        textSpan.textContent = message;
        messageDiv.appendChild(textSpan);
        
        document.body.appendChild(messageDiv);
        return messageDiv;
    }

    // Function to remove item from cart
    function removeCartItem(itemId) {
        // First find the form with CSRF token
        let form = document.querySelector(`form[data-item-id="${itemId}"]`);
        // Try alternative selectors if needed
        if (!form) {
            const forms = document.querySelectorAll('form');
            for (const f of forms) {
                if (f.querySelector('input[name="csrf_token"]')) {
                    form = f;
                    break;
                }
            }
        }
        if (!form) {
            showErrorMessage('CSRF token not found. Please refresh the page and try again.');
            console.error('No form with CSRF token found');
            return;
        }
        const csrfToken = form.querySelector('input[name="csrf_token"]')?.value;
        if (!csrfToken) {
            showErrorMessage('CSRF token not found. Please refresh the page and try again.');
            console.error('CSRF token not found');
            return;
        }

        const formData = new FormData();
        formData.append('csrf_token', csrfToken);
        fetch(`/api/cart/remove/${itemId}`, {
            method: 'POST',
            headers: {
                'X-CSRF-Token': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || data.message || `Server error: ${response.status}`);
                }).catch(e => {
                    throw new Error(`Server error: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log('Cart item removed:', data);
                showSuccessMessage('Item removed from cart');
                document.dispatchEvent(new CustomEvent('cartUpdated'));
            } else {
                const errorMsg = data.error || data.message || 'Failed to remove item from cart';
                console.error('Error removing cart item:', errorMsg);
                showErrorMessage(errorMsg);
            }
        })
        .catch(error => {
            console.error('Error removing cart item:', error);
            // Extract proper error message from error object
            let errorMessage;
            if (error instanceof Error) {
                errorMessage = error.message;
            } else if (typeof error === 'string') {
                errorMessage = error;
            } else if (error && typeof error === 'object') {
                errorMessage = error.error || error.message || JSON.stringify(error);
            } else {
                errorMessage = 'Failed to remove item from cart';
            }
            showErrorMessage(errorMessage);
        });
    }

    // Function to update cart summary section with correct totals
    function updateCartSummary(cartData) {
        if (!cartData) return;

        console.log('Updating cart summary with data:', cartData);

        try {
            // Get subtotal by summing up all item subtotals
            let calculatedSubtotal = 0;
            if (cartData.items && Array.isArray(cartData.items)) {
                calculatedSubtotal = cartData.items.reduce((total, item) => {
                    const price = item.product?.price || 0;
                    const quantity = item.quantity || 0;
                    const itemSubtotal = price * quantity;
                    console.log(`Item ${item.id}: ${item.product?.name} - Price: ${price}, Qty: ${quantity}, Subtotal: ${itemSubtotal}`);
                    return total + itemSubtotal;
                }, 0);
            } else {
                calculatedSubtotal = cartData.items.reduce((total, item) => {
                    const price = item.product?.price || 0;
                    const quantity = item.quantity || 0;
                    const itemSubtotal = price * quantity;
                    return total + itemSubtotal;
                }, 0);
            }

            // Update the summary container
            const summaryContainer = document.querySelector('.space-y-4.mb-6');
            if (summaryContainer) {
                // Update subtotal
                const summarySubtotal = summaryContainer.querySelector('.flex.justify-between:first-child .font-semibold');
                const subtotal = calculatedSubtotal || cartData.subtotal;
                if (summarySubtotal) {
                    console.log('Updated summary subtotal:', formatPrice(subtotal));
                    summarySubtotal.textContent = formatPrice(subtotal);
                }

                // Update total (could include shipping, tax, etc.)
                const summaryTotal = summaryContainer.querySelector('.border-t.border-gray-200 .text-lg.font-bold:last-child');
                const total = cartData.total || subtotal; // Use server total or fall back to subtotal
                if (summaryTotal) {
                    console.log('Updated total:', formatPrice(total));
                    summaryTotal.textContent = formatPrice(total);
                }

                // Update shipping message
                const shippingMessage = summaryContainer.querySelector('.text-sm.text-gray-500.mt-2');
                const FREE_SHIPPING_THRESHOLD = 1000000; // 1,000,000₫
                if (shippingMessage) {
                    const remaining = FREE_SHIPPING_THRESHOLD - subtotal;
                    if (remaining > 0) {
                        shippingMessage.textContent = `Add ${formatPrice(remaining)} more to get free shipping!`;
                    } else {
                        shippingMessage.textContent = 'Eligible for free shipping!';
                    }
                }
            }
        } catch (error) {
            console.error('Error updating cart summary:', error);
        }
    }

    // Hàm làm mới hoàn toàn giỏ hàng dựa trên dữ liệu từ server
    function refreshCartDisplay(cartData) {
        console.log('refreshCartDisplay called, delegating to updateUIFromCartData');
        updateUIFromCartData(cartData);
    }

    // Helper function to analyze cart structure - hỗ trợ debug
    function analyzeCartStructure() {
        console.log('Analyzing cart HTML structure...');
        const cartContainer = document.querySelector('.cart-container') || 
                            document.querySelector('.cart-items') || 
                            document.querySelector('.shopping-cart');
        
        if (!cartContainer) {
            console.warn('Cart container not found');
            return;
        }
        
        const itemElements = cartContainer.querySelectorAll('[data-item-id]');
        console.log(`Found ${itemElements.length} item elements`);
        
        itemElements.forEach(item => {
            const itemId = item.dataset.itemId;
            console.log(`Item ID: ${itemId}`);
            console.log(`  - Classes: ${item.className}`);
            
            const priceElements = item.querySelectorAll('.text-gray-900:not(.font-semibold), .item-price, .product-price');
            console.log(`  - Price elements found: ${priceElements.length}`);
            
            const subtotalElements = item.querySelectorAll('.text-gray-900.font-semibold, .item-subtotal, .product-subtotal');
            console.log(`  - Subtotal elements found: ${subtotalElements.length}`);
            
            const quantityElements = item.querySelectorAll('select.quantity-select, .item-quantity');
            console.log(`  - Quantity elements found: ${quantityElements.length}`);
        });
    }

    // Gọi hàm phân tích cấu trúc khi trang tải xong
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(analyzeCartStructure, 1000);
    });

    // Helper: Tìm phần tử HTML cho một sản phẩm
    function findItemRow(itemId) {
        // Thử nhiều cách chọn phần tử khác nhau vì mỗi template có thể đánh dấu khác nhau
        return document.querySelector(`.cart-item[data-item-id="${itemId}"]`) ||
               document.querySelector(`[data-item-id="${itemId}"]`) ||
               document.querySelector(`tr[data-item-id="${itemId}"]`) ||
               document.querySelector(`.cart-row-${itemId}`);
    }

    // Helper: Cập nhật hiển thị cho một dòng sản phẩm
    function updateItemDisplay(itemRow, price, quantity, subtotal, productName) {
        // Log the values for debugging
        console.log(`Updating display for "${productName || 'Unknown product'}"`);
        console.log(`  Price: ${price}, Quantity: ${quantity}, Calculated subtotal: ${subtotal}`);
        
        // 1. Update price display
        const priceElements = itemRow.querySelectorAll('.item-price, .product-price, .text-gray-900:not(.font-semibold):not(.item-subtotal)');
        if (priceElements.length > 0) {
            priceElements.forEach(el => {
                el.textContent = formatPrice(price);
                console.log(`  Updated price element: ${el.textContent}`);
            });
        } else {
            console.log(`  Price element not found`);
        }
        
        // 2. Update quantity display (if not select dropdown)
        const quantityDisplays = itemRow.querySelectorAll('.item-quantity-display');
        if (quantityDisplays.length > 0) {
            quantityDisplays.forEach(el => {
                el.textContent = quantity;
                console.log(`  Updated quantity display: ${quantity}`);
            });
        }
        
        // 3. Update subtotal - most important part
        const subtotalElements = itemRow.querySelectorAll('.item-subtotal, .product-subtotal, .text-gray-900.font-semibold.w-24.text-right');
        if (subtotalElements.length > 0) {
            subtotalElements.forEach(el => {
                el.textContent = formatPrice(subtotal);
                console.log(`  Updated subtotal for item ${itemId}: ${formatPrice(subtotal)}`);
            });
        } else {
            console.log(`  Subtotal element not found`);
        }
        
        // 4. Store data in data attributes for later use
        itemRow.dataset.price = price;
        itemRow.dataset.quantity = quantity;
        itemRow.dataset.subtotal = subtotal;
    }
    
    // Format number with commas and VND symbol - cải thiện để định dạng đúng
    function formatPrice(number) {
        // Đảm bảo number là một số hợp lệ
        const value = typeof number === 'string' ? parseFloat(number.replace(/[^\d.-]/g, '')) : parseFloat(number);
        
        if (isNaN(value)) {
            console.warn('Invalid price value:', number);
            return '0₫';
        }
        
        // Sử dụng Intl.NumberFormat để định dạng đúng tiền tệ Việt Nam
        return new Intl.NumberFormat('vi-VN', {
            style: 'currency',
            currency: 'VND',
            maximumFractionDigits: 0,
            currencyDisplay: 'symbol'
        }).format(value).replace('VND', '').trim() + '₫';
    }

    // NEW: Comprehensive function to update all UI elements from cart data
    function updateUIFromCartData(cartData) {
        console.log('Starting comprehensive UI update with cart data:', cartData);
        
        if (!cartData || !cartData.items) {
            console.warn('Invalid cart data received, cannot update UI');
            return;
        }
        
        // 1. Log data summary for debugging
        const itemCount = cartData.items.length;
        const totalQuantity = cartData.items.reduce((sum, item) => sum + parseInt(item.quantity, 10), 0);
        const calculatedSubtotal = cartData.items.reduce((sum, item) => {
            const price = parseFloat(item.product?.price || 0);
            const quantity = parseInt(item.quantity, 10);
            return sum + (price * quantity);
        }, 0);
        
        console.log(`Cart contains ${itemCount} unique items (${totalQuantity} total items)`);
        console.log(`Calculated subtotal: ${formatPrice(calculatedSubtotal)}`);
        console.log(`Server subtotal: ${formatPrice(cartData.subtotal)}`);
        console.log(`Server total: ${formatPrice(cartData.total)}`);
        
        // 2. Update each item row in the cart
        updateAllCartItems(cartData);
        
        // 3. Update the cart summary section
        updateCartSummary(cartData);
        
        // 4. Update the cart badge
        const cartBadge = document.getElementById('cart-badge');
        if (cartBadge) {
            cartBadge.textContent = totalQuantity;
            cartBadge.style.display = totalQuantity > 0 ? 'flex' : 'none';
        }
        
        // 5. Check for any inconsistencies between calculated values and server values
        if (Math.abs(calculatedSubtotal - cartData.subtotal) > 0.01) {
            console.warn('Inconsistency detected between calculated subtotal and server subtotal');
            console.warn(`Calculated: ${calculatedSubtotal}, Server: ${cartData.subtotal}`);
        }
        
        // 6. Update checkout button state
        const checkoutBtn = document.getElementById('checkoutBtn');
        if (checkoutBtn) {
            const hasItems = cartData.items && cartData.items.length > 0;
            checkoutBtn.disabled = !hasItems;
            checkoutBtn.title = hasItems ? '' : 'Your cart is empty';
        }
        
        console.log('Cart UI refresh completed');
    }

    // Function to update all cart items based on complete cart data - improved
    function updateAllCartItems(cartData) {
        if (!cartData.items || !Array.isArray(cartData.items)) {
            console.warn('No items found in cart data');
            return;
        }

        console.log('Updating all cart items with data:', cartData.items);

        // Loop through all items in cart
        cartData.items.forEach(item => {
            // Parse price and quantity as numbers to ensure correct calculations
            const price = parseFloat(item.price);
            const quantity = parseInt(item.quantity, 10);
            
            // Calculate subtotal correctly and log details for debugging
            const subtotal = price * quantity;
            
            console.log(`Item ${item.id}: ${item.name || 'Unknown'}`);
            console.log(`  - Price: ${price}, Qty: ${quantity}, Subtotal: ${subtotal}`);
            
            // Find the item row by its itemId
            const itemRow = findItemRow(item.id);
            
            if (itemRow) {
                // Use the comprehensive display update function
                updateItemDisplay(itemRow, price, quantity, subtotal, item.name);
            } else {
                console.warn(`Item row not found for item ID: ${item.id}. Check if data-item-id="${item.id}" exists in HTML.`);
            }
        });
    }
    
    // Function to update cart summary section with correct totals
    function updateCartSummary(cartData) {
        if (!cartData) return;

        console.log('Updating cart summary with data:', cartData);

        try {
            // Get subtotal by summing up all item subtotals
            let calculatedSubtotal = 0;
            if (cartData.items && Array.isArray(cartData.items)) {
                calculatedSubtotal = cartData.items.reduce((total, item) => {
                    const price = parseFloat(item.product?.price || 0);
                    const quantity = parseInt(item.quantity || 0, 10);
                    const itemSubtotal = price * quantity;
                    console.log(`Summary calc - Item ${item.id}: Price: ${price}, Qty: ${quantity}, Subtotal: ${itemSubtotal}`);
                    return total + itemSubtotal;
                }, 0);
            }

            // Log for debugging
            console.log(`Calculated summary subtotal: ${calculatedSubtotal}`);
            console.log(`Server summary subtotal: ${cartData.subtotal}`);

            // Update the summary container
            const summaryContainer = document.querySelector('.space-y-4.mb-6');
            if (summaryContainer) {
                // Use the server-provided subtotal, but fallback to calculated if needed
                const subtotal = (cartData.subtotal !== undefined) ? cartData.subtotal : calculatedSubtotal;
                
                // Update subtotal display
                const summarySubtotal = summaryContainer.querySelector('.flex.justify-between:first-child .font-semibold');
                if (summarySubtotal) {
                    const formattedSubtotal = formatPrice(subtotal);
                    console.log(`Updating summary subtotal display to: ${formattedSubtotal}`);
                    summarySubtotal.textContent = formattedSubtotal;
                }

                // Update total (could include shipping, tax, etc.)
                const summaryTotal = summaryContainer.querySelector('.border-t.border-gray-200 .text-lg.font-bold:last-child');
                if (summaryTotal && cartData.total !== undefined) {
                    const formattedTotal = formatPrice(cartData.total);
                    console.log(`Updating total display to: ${formattedTotal}`);
                    summaryTotal.textContent = formattedTotal;
                }

                // Update shipping message
                const shippingMessage = summaryContainer.querySelector('.text-sm.text-gray-500.mt-2');
                const FREE_SHIPPING_THRESHOLD = 1000000; // 1,000,000₫
                if (shippingMessage) {
                    const remaining = FREE_SHIPPING_THRESHOLD - subtotal;
                    if (remaining > 0) {
                        const message = `Add ${formatPrice(remaining)} more to get free shipping!`;
                        console.log(`Updating shipping message: ${message}`);
                        shippingMessage.textContent = message;
                    } else {
                        console.log('Updating shipping message: Eligible for free shipping!');
                        shippingMessage.textContent = 'Eligible for free shipping!';
                    }
                }
            }
        } catch (error) {
            console.error('Error updating cart summary:', error);
        }
    }

    // Helper: Cập nhật hiển thị cho một dòng sản phẩm - enhanced for better subtotal updating
    function updateItemDisplay(itemRow, price, quantity, subtotal, productName) {
        // Log the values for debugging
        console.log(`Updating display for "${productName || 'Unknown product'}"`);
        console.log(`  Price: ${price}, Quantity: ${quantity}, Calculated subtotal: ${subtotal}`);
        
        // 1. Update price display
        const priceElements = itemRow.querySelectorAll('.item-price, .product-price, .text-gray-900:not(.font-semibold):not(.item-subtotal)');
        if (priceElements.length > 0) {
            const formattedPrice = formatPrice(price);
            priceElements.forEach(el => {
                const previousPrice = el.textContent;
                el.textContent = formattedPrice;
                console.log(`  Updated price element: ${previousPrice} → ${formattedPrice}`);
            });
        } else {
            console.log(`  No price elements found for ${productName}`);
        }
        
        // 2. Update quantity display (if not select dropdown)
        const quantityDisplays = itemRow.querySelectorAll('.item-quantity-display');
        if (quantityDisplays.length > 0) {
            quantityDisplays.forEach(el => {
                const previousQty = el.textContent;
                el.textContent = quantity;
                console.log(`  Updated quantity display: ${previousQty} → ${quantity}`);
            });
        }
        
        // 3. Update subtotal - most important part with multiple selector attempts
        const subtotalElements = [
            ...itemRow.querySelectorAll('.item-subtotal'),
            ...itemRow.querySelectorAll('.product-subtotal'),
            ...itemRow.querySelectorAll('.text-gray-900.font-semibold.w-24.text-right'),
            ...itemRow.querySelectorAll('.text-right.font-semibold'),
            ...itemRow.querySelectorAll('[data-subtotal]')
        ];
        
        if (subtotalElements.length > 0) {
            const formattedSubtotal = formatPrice(subtotal);
            subtotalElements.forEach(el => {
                const previousSubtotal = el.textContent;
                el.textContent = formattedSubtotal;
                console.log(`  Updated subtotal: ${previousSubtotal} → ${formattedSubtotal}`);
            });
        } else {
            // If no subtotal element found, try to identify it by position or other means
            console.log(`  No dedicated subtotal elements found for ${productName}`);
            console.log(`  Attempting fallback subtotal update strategies...`);
            
            // Fallback 1: Try to find the rightmost price element in the row
            const allPriceElements = itemRow.querySelectorAll('.text-gray-900');
            if (allPriceElements.length > 1) {
                const lastPriceElement = allPriceElements[allPriceElements.length - 1];
                const previousValue = lastPriceElement.textContent;
                lastPriceElement.textContent = formatPrice(subtotal);
                console.log(`  Fallback: Updated last price element as subtotal: ${previousValue} → ${formatPrice(subtotal)}`);
            }
        }
        
        // 4. Store data in data attributes for later use
        itemRow.dataset.price = price;
        itemRow.dataset.quantity = quantity;
        itemRow.dataset.subtotal = subtotal;
        
        console.log(`  Row data attributes updated for item`);
    }
    
    // Helper: Improved item row finder with multiple selector strategies
    function findItemRow(itemId) {
        // Try multiple selector strategies to find the item row
        const itemRow = document.querySelector(`.cart-item[data-item-id="${itemId}"]`) ||
               document.querySelector(`[data-item-id="${itemId}"]`) ||
               document.querySelector(`tr[data-item-id="${itemId}"]`) ||
               document.querySelector(`.cart-row-${itemId}`);
               
        if (itemRow) {
            console.log(`Found item row for item ID ${itemId}`);
        } else {
            console.warn(`Could not find item row for item ID ${itemId}`);
        }
        
        return itemRow;
    }

});