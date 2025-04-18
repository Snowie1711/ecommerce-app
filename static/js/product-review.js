document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - Initializing review functionality');

    // Test Bootstrap and Modal functionality
    function testBootstrapModal() {
        console.log('Testing Bootstrap availability:', {
            bootstrapExists: typeof bootstrap !== 'undefined',
            modalExists: typeof bootstrap?.Modal !== 'undefined'
        });

        if (typeof bootstrap === 'undefined') {
            console.error('Bootstrap is not loaded properly. Reviews will not work.');
            return false;
        }

        return true;
    }

    if (!testBootstrapModal()) {
        console.error('Bootstrap test failed - reviews functionality may not work properly');
    }
    
    // Get references to elements
    const reviewModal = document.getElementById('reviewModal');
    const reviewForm = document.getElementById('reviewForm');
    const productIdInput = document.getElementById('productIdInput');
    const productNameElement = document.getElementById('productName');
    const submitReviewButton = document.getElementById('submitReview');

    console.log('Elements found:', {
        modal: reviewModal !== null,
        form: reviewForm !== null,
        productInput: productIdInput !== null,
        productName: productNameElement !== null,
        submitButton: submitReviewButton !== null
    });

    // Handle write review button clicks - both direct and delegated
    console.log('Setting up review button handlers');

    // Direct handlers
    const reviewButtons = document.querySelectorAll('.write-review');
    console.log('Found review buttons:', reviewButtons.length);

    // Add delegated handler for dynamically loaded buttons
    document.addEventListener('click', function(event) {
        const button = event.target.closest('.write-review');
        if (button) {
            handleReviewButtonClick(button);
        }
    });

    // Add direct handlers to existing buttons
    reviewButtons.forEach(button => button.addEventListener('click', () => handleReviewButtonClick(button)));

    function handleReviewButtonClick(button) {
        console.log('Review button clicked (either direct or delegated)');
        const productId = button.dataset.productId;
        const productName = button.dataset.productName;
        const orderId = button.dataset.orderId;
        
        console.log('Processing review button click:', {
            productId,
            productName,
            buttonElement: button
        });

        if (!productId || !productName || !orderId) {
            console.error('Missing required data attributes:', {productId, productName, orderId});
            return;
        }

        // Store orderId for submission
        reviewForm.dataset.orderId = orderId;

        // Set product info
        productIdInput.value = productId;
        productNameElement.textContent = productName;
        
        // Reset form
        reviewForm.reset();
        
        // Show modal
        if (typeof bootstrap === 'undefined') {
            console.error('Bootstrap is not loaded');
            alert('Could not initialize review form. Please refresh the page and try again.');
            return;
        }
        
        try {
            console.log('Opening modal for product:', {
                productId,
                productName,
                modalElement: reviewModal
            });
            
            // Initialize modal with options
            const modal = new bootstrap.Modal(reviewModal, {
                keyboard: true,
                backdrop: true,
                focus: true
            });
            
            modal.show();
        } catch (error) {
            console.error('Error showing modal:', error);
            alert('Could not open review form. Please refresh the page and try again.');
        }
    }

    // Handle review submission
    submitReviewButton?.addEventListener('click', async function() {
        console.log('Submit review button clicked');
        // Get form data
        const productId = productIdInput.value;
        const rating = document.querySelector('input[name="rating"]:checked')?.value;
        const comment = document.getElementById('reviewComment').value;

        // Validate form
        if (!rating) {
            alert('Please select a rating');
            return;
        }

        try {
            // Get CSRF token if available
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
            
            const headers = {
                'Content-Type': 'application/json',
            };
            
            if (csrfToken) {
                headers['X-CSRF-Token'] = csrfToken;
            }

            console.log('Submitting review:', {
                productId,
                rating,
                comment
            });
            
            // Submit review
            const response = await fetch(`/api/products/${productId}/reviews`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    rating: parseInt(rating),
                    comment: comment,
                    order_id: parseInt(reviewForm.dataset.orderId)
                })
            });

            if (response.ok) {
                // Hide modal
                bootstrap.Modal.getInstance(reviewModal).hide();
                
                // Show success message
                alert('Thank you for your review!');
                
                // Update the button for this product
                const button = document.querySelector(`.write-review[data-product-id="${productId}"]`);
                if (button) {
                    const td = button.parentElement;
                    td.innerHTML = '<span class="text-success">Reviewed</span>';
                }
                
                // Reload page after short delay to refresh content
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                const data = await response.json();
                throw new Error(data.error || 'Failed to submit review');
            }
        } catch (error) {
            console.error('Error submitting review:', error);
            alert(error.message || 'Failed to submit review. Please try again.');
        }
    });
    
    // Batch rating functionality
    const batchReviewButton = document.getElementById('rateAllProducts');
    const batchReviewModal = document.getElementById('batchReviewModal');
    const submitBatchReviewsButton = document.getElementById('submitBatchReviews');
    
    if (batchReviewButton) {
        batchReviewButton.addEventListener('click', function() {
            const modal = new bootstrap.Modal(batchReviewModal);
            modal.show();
        });
    }
    
    if (submitBatchReviewsButton) {
        submitBatchReviewsButton.addEventListener('click', async function() {
            const reviewItems = document.querySelectorAll('.product-review-item');
            const orderId = batchReviewButton.dataset.orderId;
            const ratings = [];
            
            reviewItems.forEach(item => {
                const productId = item.querySelector('.product-id').value;
                const rating = item.querySelector('input[name="rating-' + productId + '"]:checked')?.value;
                const comment = item.querySelector('.review-comment').value;
                
                if (rating) {
                    ratings.push({
                        product_id: productId,
                        rating: parseInt(rating),
                        review: comment
                    });
                }
            });
            
            if (ratings.length === 0) {
                alert('Please rate at least one product');
                return;
            }
            
            try {
                // Get CSRF token
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
                
                const headers = {
                    'Content-Type': 'application/json',
                };
                
                if (csrfToken) {
                    headers['X-CSRF-Token'] = csrfToken;
                }
                
                const response = await fetch(`/api/orders/${orderId}/rate`, {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({ ratings: ratings })
                });
                
                if (response.ok) {
                    // Hide modal
                    bootstrap.Modal.getInstance(batchReviewModal).hide();
                    
                    // Show success message
                    alert('Thank you for your reviews!');
                    
                    // Update the buttons for rated products
                    ratings.forEach(rating => {
                        const button = document.querySelector(`.write-review[data-product-id="${rating.product_id}"]`);
                        if (button) {
                            button.classList.add('btn-success');
                            button.classList.remove('btn-outline-primary');
                            button.textContent = 'Rated';
                            button.setAttribute('disabled', 'disabled');
                        }
                    });
                } else {
                    const data = await response.json();
                    throw new Error(data.error || 'Failed to submit reviews');
                }
            } catch (error) {
                console.error('Error submitting batch reviews:', error);
                alert(error.message || 'Failed to submit reviews. Please try again.');
            }
        });
    }
});