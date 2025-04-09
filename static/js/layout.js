document.addEventListener('DOMContentLoaded', function() {
    // Find the cart icon element
    const cartIconLink = document.querySelector('a[href*="/cart"]');
    
    if (cartIconLink) {
        // Check if the cart icon already has the container class
        if (!cartIconLink.classList.contains('cart-icon-container')) {
            // Wrap the cart icon contents in a span with the proper class
            const cartContents = cartIconLink.innerHTML;
            cartIconLink.classList.add('cart-icon-container');
            
            // If there's no badge yet, don't worry - the cart.js will handle it
            // Just make sure the structure is correct
            if (!cartIconLink.querySelector('#cart-badge')) {
                // Only modify if there's no badge yet
                const badgeElement = document.createElement('span');
                badgeElement.id = 'cart-badge';
                badgeElement.className = 'hidden px-2 py-1 text-xs font-bold rounded-full bg-red-500 text-white';
                cartIconLink.appendChild(badgeElement);
            }
        }
    }
});
