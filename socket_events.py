from flask_socketio import SocketIO

socketio = SocketIO()  # Initialize SocketIO independently

@socketio.on("send_message")
def handle_send_message(data):
    from app import db, Message  # Import inside function to avoid circular import
    
    sender_id = data["sender_id"]
    receiver_id = data["receiver_id"]
    content = data["content"]

    message = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.session.add(message)
    db.session.commit()

    socketio.emit("new_message", {
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "content": content,
        "timestamp": message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    }, broadcast=True)
