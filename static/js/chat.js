// Request permission for push notifications
if ('Notification' in window && 'serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js')
        .then(function(registration) {
            console.log('Service Worker registered with scope: ', registration.scope);

            // Ask for permission
            return Notification.requestPermission().then(function(permission) {
                if (permission === 'granted') {
                    console.log('Notification permission granted');
                    subscribeUserToPushNotifications(registration);
                }
            });
        })
        .catch(function(error) {
            console.error('Service Worker registration failed:', error);
        });
}

function subscribeUserToPushNotifications(registration) {
    if ('PushManager' in window) {
        registration.pushManager.subscribe({
            userVisibleOnly: true, // Allow visible notifications
            applicationServerKey: urlBase64ToUint8Array('<YOUR_PUBLIC_VAPID_KEY>') // Replace with your public VAPID key
        })
        .then(function(subscription) {
            console.log('User is subscribed:', subscription);

            // Save the subscription details to your server (for later sending notifications)
            sendSubscriptionToServer(subscription);
        })
        .catch(function(error) {
            console.error('Failed to subscribe the user: ', error);
        });
    }
}

// Convert VAPID public key to a Uint8Array (for the subscription process)
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/\_/g, '/');
    const rawData = atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}
