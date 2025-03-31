document.addEventListener('DOMContentLoaded', function() {
    // Search functionality
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
    const filterForm = document.getElementById('filterForm');
    let searchTimeout;

    // Handle form submissions
    if (filterForm) {
        filterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            fetchFilteredProducts();
        });

        // Handle price inputs with debouncing
        const priceInputs = document.querySelectorAll('#min_price, #max_price');
        priceInputs.forEach(input => {
            input.addEventListener('input', debounce(() => fetchFilteredProducts(), 500));
        });

        // Handle other filter changes
        document.querySelectorAll('#filterForm select:not(#category)').forEach(select => {
            select.addEventListener('change', () => fetchFilteredProducts());
        });

        // Handle search input with debouncing
        const searchFilter = document.getElementById('search');
        if (searchFilter) {
            searchFilter.addEventListener('input', debounce(() => fetchFilteredProducts(), 500));
        }
    }

    // Live search functionality
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            if (query.length === 0) {
                searchResults.classList.add('hidden');
                return;
            }

            searchResults.innerHTML = '<div class="p-4 text-gray-500">Searching...</div>';
            searchResults.classList.remove('hidden');

            searchTimeout = setTimeout(() => {
                fetchSearchResults(query);
            }, 300);
        });

        // Close search results when clicking outside
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.classList.add('hidden');
            }
        });
    }

    // Pagination handling
    document.addEventListener('click', (e) => {
        if (e.target.matches('.pagination-link')) {
            e.preventDefault();
            fetchFilteredProducts(new URLSearchParams(new URL(e.target.href).search));
        }
    });

    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    async function fetchFilteredProducts(searchParams = null) {
        const container = document.getElementById('productsContainer');
        if (!container) return;

        // Show loading state
        container.innerHTML = `
            <div class="text-center py-12">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p class="text-gray-500">Loading products...</p>
            </div>
        `;

        try {
            const params = searchParams || new URLSearchParams(new FormData(filterForm));
            
            // Ensure category is properly encoded
            const category = params.get('category');
            if (category) {
                params.set('category', encodeURIComponent(category));
            }
            
            const response = await fetch(`/api/products?${params.toString()}`);
            const data = await response.json();
            
            if (data.success) {
                updateProductsDisplay(data.products, data.total, data.current_page, data.pages);
                
                // Update URL without page reload
                const newUrl = `${window.location.pathname}?${params.toString()}`;
                window.history.pushState({ path: newUrl }, '', newUrl);

                // Reinitialize Add to Cart forms
                initializeAddToCartForms();
            } else {
                console.error('Error:', data.error);
                showError('Failed to load products');
            }
        } catch (error) {
            console.error('Error fetching products:', error);
            showError('Failed to load products');
        }
    }

    function initializeAddToCartForms() {
        document.querySelectorAll('.add-to-cart-form').forEach(form => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const button = form.querySelector('button[type="submit"]');
                const originalText = button.textContent;
                button.disabled = true;
                button.textContent = 'Adding...';

                try {
                    const response = await fetch(form.action, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrfToken
                        }
                    });
                    
                    if (response.ok) {
                        button.textContent = 'Added!';
                        button.classList.remove('bg-blue-600', 'hover:bg-blue-700');
                        button.classList.add('bg-green-600');
                        setTimeout(() => {
                            button.textContent = originalText;
                            button.classList.remove('bg-green-600');
                            button.classList.add('bg-blue-600', 'hover:bg-blue-700');
                            button.disabled = false;
                        }, 2000);
                    } else {
                        throw new Error('Failed to add to cart');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    button.textContent = 'Error';
                    button.classList.add('bg-red-600');
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.classList.remove('bg-red-600');
                        button.classList.add('bg-blue-600');
                        button.disabled = false;
                    }, 2000);
                }
            });
        });
    }

    function fetchSearchResults(query) {
        fetch(`/api/products?search=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.products.length > 0) {
                    displaySearchResults(data.products);
                } else {
                    searchResults.innerHTML = '<div class="p-4 text-gray-500">No products found</div>';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                searchResults.innerHTML = '<div class="p-4 text-red-500">Error fetching results</div>';
            });
    }

    function updateProductsDisplay(products, total, currentPage, totalPages) {
        const container = document.getElementById('productsContainer');
        if (!container) return;

        if (products.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12">
                    <i class="fas fa-search text-gray-400 text-4xl mb-4"></i>
                    <h3 class="text-xl font-semibold text-gray-700 mb-2">No Products Found</h3>
                    <p class="text-gray-500">Try adjusting your search or filter to find what you're looking for.</p>
                </div>
            `;
            return;
        }

        let productsHTML = '<div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">';
        products.forEach(product => {
            productsHTML += generateProductCard(product);
        });
        productsHTML += '</div>';

        if (totalPages > 1) {
            productsHTML += generatePaginationHTML(currentPage, totalPages);
        }

        container.innerHTML = productsHTML;
    }

    function generateProductCard(product) {
        return `
            <div class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition duration-300">
                <a href="/products/${product.id}" class="block">
                    ${product.image_url
                        ? `<img src="/static/uploads/${product.image_url}" alt="${product.name}" class="w-full h-48 object-cover">`
                        : `<div class="w-full h-48 bg-gray-200 flex items-center justify-center">
                            <i class="fas fa-image text-gray-400 text-4xl"></i>
                           </div>`
                    }
                    <div class="p-4">
                        <h3 class="text-lg font-semibold mb-2 line-clamp-1">${product.name}</h3>
                        <p class="text-gray-600 mb-2 text-sm line-clamp-2">${product.description}</p>
                        <div class="flex justify-between items-center">
                            <span class="text-blue-600 font-bold">$${product.price.toFixed(2)}</span>
                            <span class="text-sm text-gray-500">
                                ${product.stock > 0 ? `${product.stock} in stock` : 'Out of stock'}
                            </span>
                        </div>
                    </div>
                </a>
                ${product.stock > 0
                    ? `<div class="px-4 pb-4">
                        <form action="/cart/add/${product.id}" method="POST" class="add-to-cart-form">
                            <input type="hidden" name="csrf_token" value="${csrfToken}">
                            <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 transition duration-300">
                                Add to Cart
                            </button>
                        </form>
                       </div>`
                    : `<div class="px-4 pb-4">
                        <button disabled class="w-full bg-gray-300 text-gray-500 py-2 rounded-lg font-semibold cursor-not-allowed">
                            Out of Stock
                        </button>
                       </div>`
                }
            </div>
        `;
    }

    function generatePaginationHTML(currentPage, totalPages) {
        const params = new URLSearchParams(window.location.search);
        params.delete('page');

        let paginationHTML = `
            <div class="mt-8 flex justify-center">
                <nav class="flex space-x-2" aria-label="Pagination">
        `;

        if (currentPage > 1) {
            params.set('page', currentPage - 1);
            paginationHTML += `
                <a href="?${params.toString()}" class="pagination-link px-4 py-2 border border-gray-300 rounded-lg text-blue-600 hover:bg-blue-50">
                    Previous
                </a>
            `;
        }

        for (let i = 1; i <= totalPages; i++) {
            params.set('page', i);
            if (i === currentPage) {
                paginationHTML += `
                    <span class="px-4 py-2 border border-blue-600 rounded-lg bg-blue-600 text-white">
                        ${i}
                    </span>
                `;
            } else {
                paginationHTML += `
                    <a href="?${params.toString()}" class="pagination-link px-4 py-2 border border-gray-300 rounded-lg text-blue-600 hover:bg-blue-50">
                        ${i}
                    </a>
                `;
            }
        }

        if (currentPage < totalPages) {
            params.set('page', currentPage + 1);
            paginationHTML += `
                <a href="?${params.toString()}" class="pagination-link px-4 py-2 border border-gray-300 rounded-lg text-blue-600 hover:bg-blue-50">
                    Next
                </a>
            `;
        }

        paginationHTML += `
                </nav>
            </div>
        `;
        
        return paginationHTML;
    }

    function displaySearchResults(products) {
        const html = products.map(product => `
            <a href="/products/${product.id}" class="block hover:bg-gray-50">
                <div class="flex items-center p-4 border-b border-gray-100">
                    ${product.image_url ? 
                        `<img src="/static/uploads/${product.image_url}" alt="${product.name}" class="w-12 h-12 object-cover rounded mr-4">` :
                        '<div class="w-12 h-12 bg-gray-200 rounded mr-4 flex items-center justify-center"><i class="fas fa-image text-gray-400"></i></div>'
                    }
                    <div class="flex-1">
                        <h4 class="text-sm font-medium text-gray-900">${product.name}</h4>
                        <p class="text-sm text-gray-500">$${product.price.toFixed(2)}</p>
                    </div>
                    ${product.is_in_stock ? 
                        '<span class="text-xs text-green-600">In Stock</span>' :
                        '<span class="text-xs text-red-600">Out of Stock</span>'
                    }
                </div>
            </a>
        `).join('');

        searchResults.innerHTML = html;
    }

    function showError(message) {
        const container = document.getElementById('productsContainer');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-12">
                    <i class="fas fa-exclamation-circle text-red-500 text-4xl mb-4"></i>
                    <h3 class="text-xl font-semibold text-red-700 mb-2">Error</h3>
                    <p class="text-gray-500">${message}</p>
                </div>
            `;
        }
    }

    // Handle browser back/forward
    window.addEventListener('popstate', () => {
        fetchFilteredProducts(new URLSearchParams(window.location.search));
    });
});