from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from flask import request, redirect, url_for
from datetime import datetime
from flask_socketio import SocketIO

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SECRET_KEY"] = "your_secret_key"  # For session security

db = SQLAlchemy(app)
login_manager = LoginManager(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)    
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create the database and tables
with app.app_context():
    db.create_all()

@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = request.form["password"]
    user = User(username=username, password=password)
    db.session.add(user)
    db.session.commit()
    return redirect(url_for("home"))

@app.route("/send_message", methods=["POST"])
def send_message():
    sender_id = request.form["sender_id"]
    receiver_id = request.form["receiver_id"]
    content = request.form["content"]

    message = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.session.add(message)
    db.session.commit()

    return "Message sent successfully!"

@app.route("/home")
def home():
    users = User.query.all()
    messages = Message.query.order_by(Message.timestamp.desc()).all()
    return f"""
    <h1>Welcome to FreeConnect</h1>
    <a href='/register_form'>Register</a> | <a href='/send_message_form'>Send Message</a> | <a href='/chat'>Live Chat</a>
    <h2>Users:</h2>
    <ul>{"".join(f"<li>{user.username}</li>" for user in users)}</ul>
    <h2>Messages:</h2>
    <ul>
        {"".join(f"<li><strong>From {m.sender_id} to {m.receiver_id}:</strong> {m.content} at {m.timestamp}</li>" for m in messages)}
    </ul>
    """

@app.route("/register_form")
def register_form():
    return """
    <h2>Register</h2>
    <form action="/register" method="post">
        <label>Username:</label> <input type="text" name="username" required><br>
        <label>Password:</label> <input type="password" name="password" required><br>
        <button type="submit">Register</button>
    </form>
    <a href='/home'>Go to Home</a>
    """
    
socketio = SocketIO(app)

@socketio.on("message")
def handle_message(data):
    print(f"Received message: {data}")
    socketio.emit("message", data)



def chat():
    return """
    <h2>Live Chat</h2>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <script>
        var socket = io.connect("http://127.0.0.1:5000");
        socket.on("message", function(data) {
            var chatBox = document.getElementById("chat-box");
            chatBox.innerHTML += "<p>" + data + "</p>";
        });

        function sendMessage() {
            var message = document.getElementById("message").value;
            socket.emit("message", message);
        }
    </script>
    <div id="chat-box"></div>
    <input type="text" id="message"><button onclick="sendMessage()">Send</button>
    """

    
@app.route("/send_message_form")
def send_message_form():
    users = User.query.all()
    user_options = "".join(f'<option value="{user.id}">{user.username}</option>' for user in users)

    return f"""
    <h2>Send Message</h2>
    <form action="/send_message" method="post">
        <label>Sender:</label> 
        <select name="sender_id">{user_options}</select><br>
        <label>Receiver:</label> 
        <select name="receiver_id">{user_options}</select><br>
        <label>Message:</label> <textarea name="content" required></textarea><br>
        <button type="submit">Send</button>
    </form>
    <a href='/home'>Go to Home</a>
    """
@app.route("/chat")
def chat_page():
    return chat()
@app.route("/")
def index():
    return redirect(url_for("home"))

   
if __name__ == "__main__":
    socketio.run(app, debug=True)

