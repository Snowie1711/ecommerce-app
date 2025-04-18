document.addEventListener('DOMContentLoaded', function() {
    // Event listener for cancel request
    document.addEventListener('click', function(e) {
        // Check if clicked element is a cancel button with data-order-id
        if (e.target && e.target.matches('button[data-order-id]')) {
            const orderId = e.target.dataset.orderId;
            
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            
            fetch(`/orders/${orderId}/request-cancel`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    reason: "User requested cancellation"
                })
            })
            .then(async res => {
                const data = await res.json();
                if (res.ok) {
                    alert("Đã gửi yêu cầu hủy, chờ admin xác nhận.");
                    location.reload();
                } else {
                    // Show specific error message from server
                    alert(data.error || "Không thể gửi yêu cầu. Vui lòng thử lại.");
                }
            })
            .catch(err => {
                console.error("Lỗi khi gửi yêu cầu hủy:", err);
                alert("Lỗi kết nối máy chủ. Vui lòng thử lại sau.");
            });
        }
    });
});

// Function to handle rejection of cancellation requests
function rejectCancel(orderId, button) {
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    fetch(`/admin/orders/${orderId}/reject-cancellation`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(async res => {
        const data = await res.json();
        if (res.ok) {
            // Find and remove the row from table
            const row = button.closest('tr');
            if (row) {
                row.remove();
                
                // Check if table is empty and add "No requests" message if needed
                const tbody = document.querySelector('table tbody');
                if (!tbody.querySelector('tr')) {
                    const emptyRow = document.createElement('tr');
                    emptyRow.innerHTML = '<td colspan="6" class="text-center">No cancellation requests found.</td>';
                    tbody.appendChild(emptyRow);
                }
            }
            
            // Show success message
            alert("Đã từ chối yêu cầu hủy đơn.");
        } else {
            // Show error message from server
            alert(data.error || "Lỗi khi xử lý từ chối yêu cầu.");
        }
    })
    .catch(err => {
        console.error("Lỗi:", err);
        alert("Lỗi kết nối máy chủ.");
    });
}