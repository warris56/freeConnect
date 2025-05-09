// service-worker.js

self.addEventListener('push', function(event) {
    const options = {
        body: event.data.text(),
        icon: '/static/icons/notification-icon.png', // Add your notification icon here
        badge: '/static/icons/notification-badge.png', // Add your notification badge here
        tag: 'new-message'
    };

    event.waitUntil(
        self.registration.showNotification('New Message', options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow('/chat') // Open the chat page or relevant page
    );
});
