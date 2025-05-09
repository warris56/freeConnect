from flask import emit
from app import db, Message, load_user
from datetime import datetime

@socketio.on("join_room")
def handle_join_room(data):
    user_id = data["user_id"]
    partner_id = data["partner_id"]

    # ✅ Ensure both users enter the same chat room
    chat_room = f'chat_{min(user_id, partner_id)}_{max(user_id, partner_id)}'
    join_room(chat_room)
    print(f'User {user_id} joined room {chat_room}')

@socketio.on("message")
def handle_message(data):
    user = load_user(data["sender_id"])  # ✅ Ensure session loads correctly
    if not user:
        return

    receiver_id = data.get("receiver_id")
    content = data.get("content")

    if receiver_id and content:
        msg = Message(sender_id=user.id, receiver_id=receiver_id, content=content)
        db.session.add(msg)
        db.session.commit()

        # ✅ Use shared chat room for instant updates
        chat_room = f'chat_{min(user.id, receiver_id)}_{max(user.id, receiver_id)}'

        emit("new_message", {
            "content": content,
            "timestamp": datetime.utcnow().strftime("%H:%M"),
            "sender_id": user.id,
            "receiver_id": receiver_id
        }, room=chat_room)

