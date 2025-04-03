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

    // Update all cart forms to dispatch cartUpdated event
    document.querySelectorAll('form').forEach(form => {
        if (form.action.includes('/cart/')) {
            form.addEventListener('submit', function() {
                // Let the form submit complete
                setTimeout(() => {
                    // Dispatch cartUpdated event
                    document.dispatchEvent(new CustomEvent('cartUpdated'));
                }, 100);
            });
        }
    });

    // Handle quantity select changes
    document.querySelectorAll('select[name="quantity"]').forEach(select => {
        select.addEventListener('change', function() {
            // Let the form submit complete
            setTimeout(() => {
                // Dispatch cartUpdated event
                document.dispatchEvent(new CustomEvent('cartUpdated'));
            }, 100);
        });
    });
});