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
                    const itemCount = data.total_items || 0;
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
        if (form.action.includes('/cart/add/')) {
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const productId = form.action.split('/cart/add/')[1];
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
                        throw new Error(data.error || 'Error adding item to cart');
                    }

                    // Show success message
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded shadow-lg';
                    messageDiv.textContent = 'Item added to cart successfully!';
                    document.body.appendChild(messageDiv);

                    // Remove message after 3 seconds
                    setTimeout(() => {
                        messageDiv.remove();
                    }, 3000);

                    // Update cart badge
                    document.dispatchEvent(new CustomEvent('cartUpdated'));

                } catch (error) {
                    alert(error.message);
                }
            });
        } else if (form.action.includes('/cart/')) {
            // For other cart forms (remove, update) - keep original behavior
            form.addEventListener('submit', function() {
                setTimeout(() => {
                    document.dispatchEvent(new CustomEvent('cartUpdated'));
                }, 100);
            });
        }
    });

    // Format number with commas and VND symbol
    function formatPrice(number) {
        const value = parseFloat(number);
        if (isNaN(value)) {
            return '0₫';
        }
        return new Intl.NumberFormat('vi-VN', {
            maximumFractionDigits: 0
        }).format(value) + '₫';
    }

    // Update cart prices
    function updateCartPrices(data) {
        try {
            // Find the item container first
            const container = document.querySelector('select[name="quantity"]')?.closest('.flex.items-center.space-x-4');
            
            // Update individual item subtotal if container found
            if (container) {
                const subtotalElement = container.querySelector('.text-gray-900.font-semibold.w-24.text-right');
                if (subtotalElement && data.subtotal) {
                    subtotalElement.textContent = formatPrice(data.subtotal);
                }
            }

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
                        shippingMessage.textContent = '';
                    }
                }
            }
        } catch (error) {
            console.error('Error updating cart prices:', error);
        }
    }

    // Handle quantity select changes
    document.querySelectorAll('select[name="quantity"]').forEach(select => {
        if (!select.disabled) {
            // Store initial value
            select.dataset.originalValue = select.value;
            
            select.addEventListener('change', async function(e) {
                e.preventDefault();
                const form = this.closest('form');
                if (!form) return;

                const productId = this.dataset.productId;
                const quantity = parseInt(this.value, 10);
                const originalValue = parseInt(this.dataset.originalValue, 10);
                const csrfToken = form.querySelector('input[name="csrf_token"]').value;

                try {
                    // Show loading state
                    this.disabled = true;
                    
                    const formData = new FormData();
                    formData.append('quantity', quantity);
                    formData.append('csrf_token', csrfToken);
                    if (this.dataset.size) formData.append('size', this.dataset.size);
                    if (this.dataset.colorId) formData.append('color_id', this.dataset.colorId);

                    const response = await fetch(`/cart/update/${productId}`, {
                        method: 'POST',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: formData
                    });

                    const data = await response.json();
                    
                    if (!response.ok || data.error) {
                        throw new Error(data.error || 'Failed to update cart');
                    }

                    // Parse the numeric values from the response
                    const subtotal = parseFloat(data.subtotal);
                    const total = parseFloat(data.total);
                    
                    if (isNaN(subtotal) || isNaN(total)) {
                        throw new Error('Invalid response data');
                    }
                    
                    data.subtotal = subtotal;
                    data.total = total;

                    // Update prices in the UI
                    updateCartPrices(data);

                    // Store new value as previous value
                    this.dataset.originalValue = quantity.toString();

                    // Dispatch cart updated event
                    document.dispatchEvent(new CustomEvent('cartUpdated'));

                } catch (error) {
                    console.error('Error updating cart:', error);
                    // Revert to previous value
                    this.value = originalValue.toString();
                    alert(error.message || 'Failed to update cart');
                } finally {
                    // Re-enable select
                    this.disabled = false;
                }
            });
        }
    });

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

            if (!response.ok) {
                throw new Error('Failed to fetch stock information');
            }

            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
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

    // Update available quantities when size or color changes
    const sizeSelect = document.getElementById('size');
    const colorInputs = document.querySelectorAll('input[name="color_id"]');
    
    if (sizeSelect) {
        sizeSelect.addEventListener('change', updateQuantityOptions);
    }
    
    colorInputs.forEach(input => {
        input.addEventListener('change', updateQuantityOptions);
    });

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
    function updateCartItemQuantity(itemId, quantity) {
        fetch(`/api/cart/update/${itemId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ quantity })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Cart item quantity updated:', data);
                document.dispatchEvent(new CustomEvent('cartUpdated'));
            } else {
                console.error('Error updating cart item quantity:', data.error);
            }
        })
        .catch(error => console.error('Error updating cart item quantity:', error));
    }

    // Function to remove item from cart
    function removeCartItem(itemId) {
        fetch(`/api/cart/remove/${itemId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Cart item removed:', data);
                document.dispatchEvent(new CustomEvent('cartUpdated'));
            } else {
                console.error('Error removing cart item:', data.error);
            }
        })
        .catch(error => console.error('Error removing cart item:', error));
    }
});