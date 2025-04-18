// Global variables
let sortBy;
let productsTable;

// Make fetchAdminProducts globally available
window.fetchAdminProducts = async function(page = 1) {
    const params = new URLSearchParams();
    if (categoryFilter.value) params.set('category', categoryFilter.value);
    if (sortBy.value) params.set('sort', sortBy.value);
    params.set('page', page);

    // Show loading state
    productsTable.innerHTML = `
        <tr>
            <td colspan="7" class="text-center py-4">
                <div class="flex justify-center items-center">
                    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                    <span class="ml-2 text-gray-600">Loading products...</span>
                </div>
            </td>
        </tr>
    `;

    try {
        const response = await fetch(`/api/admin/products?${params.toString()}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            }
        });
        const data = await response.json();

        // Data format: {items: [], total: number, pages: number, page: number}
        if (data.items) {
            updateProductsTable(data.items);
            updatePagination(data.page, data.pages);
            updateUrl(params);
        } else {
            showError('Failed to load products');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Failed to load products');
    }
}

// Helper functions
function updateProductsTable(products) {
    productsTable.innerHTML = products.map(product => `
            <tr>
                <td class="px-6 py-4 whitespace-nowrap">
                    ${product.image_url 
                        ? `<img src="/static/uploads/${product.image_url}" alt="${product.name}" class="h-16 w-16 object-cover rounded">`
                        : `<div class="h-16 w-16 bg-gray-100 flex items-center justify-center rounded">
                            <i class="fas fa-image text-gray-400 text-xl"></i>
                           </div>`
                    }
                </td>
                <td class="px-6 py-4">
                    <div class="text-sm font-medium text-gray-900">${product.name}</div>
                    <div class="text-sm text-gray-500">SKU: ${product.sku}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                        ${product.category_name}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">${product.price_display}₫</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="${product.stock < 10 ? 'text-red-600' : 'text-gray-900'}">
                        ${product.stock}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                        ${product.is_active 
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'}">
                        ${product.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <a href="/admin/products/${product.id}/edit"
                       class="text-indigo-600 hover:text-indigo-900 mr-3">Edit</a>
                    <button onclick="deleteProduct(${product.id})"
                            class="text-red-600 hover:text-red-900">Delete</button>
                </td>
            </tr>
        `).join('');
    }

function updatePagination(currentPage, totalPages) {
    const paginationContainer = document.querySelector('.pagination');
        if (!paginationContainer || totalPages <= 1) return;

        let paginationHTML = `<nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">`;

        // Previous button
        if (currentPage > 1) {
            paginationHTML += `
                <button class="pagination-btn relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
                        data-page="${currentPage - 1}">
                    Previous
                </button>
            `;
        }

        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === currentPage) {
                paginationHTML += `
                    <span class="relative inline-flex items-center px-4 py-2 border border-indigo-500 bg-indigo-50 text-sm font-medium text-indigo-600">
                        ${i}
                    </span>
                `;
            } else {
                paginationHTML += `
                    <button class="pagination-btn relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
                            data-page="${i}">
                        ${i}
                    </button>
                `;
            }
        }

        // Next button
        if (currentPage < totalPages) {
            paginationHTML += `
                <button class="pagination-btn relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
                        data-page="${currentPage + 1}">
                    Next
                </button>
            `;
        }

        paginationHTML += '</nav>';
        paginationContainer.innerHTML = paginationHTML;

        // Add event listeners to pagination buttons
        document.querySelectorAll('.pagination-btn').forEach(button => {
            button.addEventListener('click', () => {
                const page = parseInt(button.dataset.page);
                window.fetchAdminProducts(page);
            });
        });
    }

function updateUrl(params) {
    const newUrl = `${window.location.pathname}?${params.toString()}`;
        window.history.pushState({ path: newUrl }, '', newUrl);
    }

function showError(message) {
    productsTable.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-8">
                    <div class="text-red-500 mb-2">
                        <i class="fas fa-exclamation-circle text-xl"></i>
                    </div>
                    <p class="text-gray-500">${message}</p>
                </td>
            </tr>
        `;
    }

document.addEventListener('DOMContentLoaded', function() {
    // Initialize global variables
    categoryFilter = document.getElementById('categoryFilter');
    sortBy = document.getElementById('sortBy');
    productsTable = document.querySelector('table tbody');

    // Get the current search parameters
    const urlParams = new URLSearchParams(window.location.search);
    const isSearchMode = urlParams.get('search') !== null;

    if (!isSearchMode) {
        // Set up event listeners only if not in search mode
        categoryFilter.addEventListener('change', () => window.fetchAdminProducts(1));
        sortBy.addEventListener('change', () => window.fetchAdminProducts(1));

        // Handle browser back/forward
        window.addEventListener('popstate', () => {
            const params = new URLSearchParams(window.location.search);
            const page = parseInt(params.get('page')) || 1;
            categoryFilter.value = params.get('category') || '';
            sortBy.value = params.get('sort') || 'name';
            window.fetchAdminProducts(page);
        });

        // Initial load of products
        const initialPage = parseInt(urlParams.get('page')) || 1;
        window.fetchAdminProducts(initialPage);
    }
});

// Delete product function (global scope for onclick access)
window.deleteProduct = async function(productId) {
    if (!confirm('Are you sure you want to delete this product? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/admin/products/${productId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });

        if (response.ok) {
            // Reload the current page of products
            const params = new URLSearchParams(window.location.search);
            const pageNum = parseInt(params.get('page')) || 1;
            window.fetchAdminProducts(pageNum);
        } else {
            throw new Error('Failed to delete product');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error deleting product');
    }
};