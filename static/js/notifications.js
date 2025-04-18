document.addEventListener('DOMContentLoaded', function() {
    const notificationBell = document.getElementById('notification-bell');
    const notificationDropdown = document.getElementById('notification-dropdown');
    const notificationBadge = document.getElementById('notification-badge');
    const notificationList = document.getElementById('notification-list');

    // Initialize Socket.IO
    const socket = io({
        path: '/socket.io',
        transports: ['websocket'],
        upgrade: false
    });

    // Listen for new notifications
    socket.on('notification', function(data) {
        updateNotificationBadge(data.unreadCount);
        if (!notificationDropdown.classList.contains('hidden')) {
            loadNotifications();
        }
    });

    // Function to update notification badge
    function updateNotificationBadge(count) {
        if (count > 0) {
            notificationBadge.textContent = count;
            notificationBadge.classList.remove('hidden');
        } else {
            notificationBadge.classList.add('hidden');
        }
    }

    // Function to load notifications
    function loadNotifications() {
        fetch('/api/notifications')
            .then(response => response.json())
            .then(data => {
                notificationList.innerHTML = '';
                if (data.notifications.length === 0) {
                    notificationList.innerHTML = '<li class="py-2 px-4 text-gray-500 text-center">No notifications</li>';
                    return;
                }
                
                data.notifications.forEach(notification => {
                    const li = document.createElement('li');
                    li.className = `notification-item py-2 px-4 border-b last:border-b-0 ${notification.is_read ? '' : 'unread'}`;
                    
                    const link = document.createElement('a');
                    link.href = notification.link || '#';
                    link.className = 'block hover:bg-gray-50 rounded transition-colors duration-200';
                    link.innerHTML = `
                        <div class="flex items-center justify-between">
                            <div class="text-sm ${notification.is_read ? 'text-gray-600' : 'text-gray-900 font-medium'}">
                                ${notification.message}
                            </div>
                            ${!notification.is_read ? '<span class="inline-block w-2 h-2 bg-blue-500 rounded-full ml-2"></span>' : ''}
                        </div>
                        <div class="text-xs text-gray-500 mt-1">
                            ${new Date(notification.created_at).toLocaleString()}
                        </div>
                    `;
                    
                    if (!notification.is_read) {
                        link.addEventListener('click', (e) => {
                            if (notification.link) {
                                e.preventDefault();
                                markNotificationAsRead(notification.id)
                                    .then(() => window.location.href = notification.link);
                            } else {
                                markNotificationAsRead(notification.id);
                            }
                        });
                    }
                    
                    li.appendChild(link);
                    notificationList.appendChild(li);
                });
            })
            .catch(error => console.error('Error loading notifications:', error));
    }

    // Function to mark notification as read
    function markNotificationAsRead(notificationId) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
        return fetch(`/api/notifications/${notificationId}/read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Get updated unread count
                fetch('/api/notifications/unread')
                    .then(response => response.json())
                    .then(data => updateNotificationBadge(data.count));
            }
            return data;
        })
        .catch(error => console.error('Error marking notification as read:', error));
    }

    // Toggle dropdown on bell click
    if (notificationBell) {
        notificationBell.addEventListener('click', function(e) {
            e.preventDefault();
            notificationDropdown.classList.toggle('hidden');
            if (!notificationDropdown.classList.contains('hidden')) {
                loadNotifications();
            }
        });
    }

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (notificationDropdown && !notificationBell.contains(e.target) && !notificationDropdown.contains(e.target)) {
            notificationDropdown.classList.add('hidden');
        }
    });

    // Initial load
    fetch('/api/notifications/unread')
        .then(response => response.json())
        .then(data => updateNotificationBadge(data.count))
        .catch(error => console.error('Error getting initial unread count:', error));
});