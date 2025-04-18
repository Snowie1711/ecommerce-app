document.addEventListener('DOMContentLoaded', function() {
    const searchInputs = document.querySelectorAll('[data-search-input]');
    
    searchInputs.forEach(input => {
        const container = input.parentElement;
        
        // Create suggestions dropdown
        const dropdown = document.createElement('div');
        dropdown.className = 'search-suggestions hidden absolute left-0 right-0 mt-1 bg-white border rounded-lg shadow-lg z-50';
        container.appendChild(dropdown);
        
        let debounceTimer;
        
        input.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            const query = this.value.trim();
            
            if (query.length === 0) {
                dropdown.classList.add('hidden');
                return;
            }
            
            // Debounce requests to avoid too many API calls
            debounceTimer = setTimeout(() => {
                fetch(`/api/search/suggestions?q=${encodeURIComponent(query)}`)
                    .then(response => response.json())
                    .then(suggestions => {
                        if (suggestions.length === 0) {
                            dropdown.classList.add('hidden');
                            return;
                        }
                        
                        // Build suggestions HTML
                        const html = suggestions.map(product => `
                            <a href="${product.url}" class="flex items-center p-2 hover:bg-gray-100">
                                <img src="${product.image}" alt="${product.name}" class="w-12 h-12 object-cover rounded">
                                <div class="ml-3">
                                    <div class="text-sm font-medium text-gray-900">${product.name}</div>
                                    <div class="text-sm text-gray-500">${product.price}₫</div>
                                </div>
                            </a>
                        `).join('');
                        
                        dropdown.innerHTML = html;
                        dropdown.classList.remove('hidden');
                    })
                    .catch(error => {
                        console.error('Error fetching search suggestions:', error);
                        dropdown.classList.add('hidden');
                    });
            }, 300); // Wait 300ms after last keystroke before searching
        });
        
        // Hide dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!container.contains(e.target)) {
                dropdown.classList.add('hidden');
            }
        });
        
        // Handle keyboard navigation
        input.addEventListener('keydown', function(e) {
            const items = dropdown.querySelectorAll('a');
            const currentIndex = Array.from(items).findIndex(item => item === document.activeElement);
            
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    if (currentIndex < items.length - 1) {
                        items[currentIndex + 1].focus();
                    } else {
                        items[0].focus();
                    }
                    break;
                    
                case 'ArrowUp':
                    e.preventDefault();
                    if (currentIndex > 0) {
                        items[currentIndex - 1].focus();
                    } else {
                        items[items.length - 1].focus();
                    }
                    break;
                    
                case 'Escape':
                    dropdown.classList.add('hidden');
                    input.blur();
                    break;
            }
        });
    });
});