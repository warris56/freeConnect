from flask import emit
from datetime import datetime

@socketio.on('message')
def handle_message(data):
    if not current_user.is_authenticated:
        return  # Ignore if the user is not logged in

    receiver_id = data.get('receiver_id')
    content = data.get('content')

    if receiver_id and content:
        # Save to DB
        msg = Message(sender_id=current_user.id, receiver_id=receiver_id, content=content)
        db.session.add(msg)
        db.session.commit()

        # Emit the message to both sender and receiver
        emit('new_message', {
            'content': content,
            'timestamp': datetime.utcnow().strftime('%H:%M'),
            'sender_id': current_user.id,
            'receiver_id': receiver_id
        }, room=f'user_{receiver_id}')
        
        emit('new_message', {
            'content': content,
            'timestamp': datetime.utcnow().strftime('%H:%M'),
            'sender_id': current_user.id,
            'receiver_id': receiver_id
        }, room=f'user_{current_user.id}')

        # Emit a notification to the receiver
        emit('new_notification', {
            'message': f'You have a new message from {current_user.username}',
            'sender_id': current_user.id
        }, room=f'user_{receiver_id}')
