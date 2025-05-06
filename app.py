from flask import Flask
from flask_login import login_required
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from flask_migrate import Migrate
from flask import request, redirect, url_for
from datetime import datetime
from flask_socketio import SocketIO
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SECRET_KEY"] = "your_secret_key"  # For session security



db = SQLAlchemy(app)  # Initialize the database
migrate = Migrate(app, db)  # Initialize migration AFTER defining `db`
login_manager = LoginManager(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
       
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
    
    user = User(username=username)
    user.set_password(password)  # Hash the password before storing
    
    db.session.add(user)
    db.session.commit()
    return redirect(url_for("home"))

@app.route("/send_message", methods=["POST"])
@login_required
def send_message():
    sender_id = request.form.get("sender_id")  # Use `.get()` to avoid errors
    receiver_id = request.form.get("receiver_id")
    content = request.form.get("content")

    if not sender_id or not receiver_id or not content:
        return "Error: Missing sender, receiver, or message content!", 400

    message = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.session.add(message)
    db.session.commit()

    return redirect(url_for("home"))


@app.route("/home")
def home():
    if not current_user.is_authenticated:
        return redirect(url_for("login_form"))

    messages = Message.query.filter(
        (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
    ).order_by(Message.timestamp.desc()).all()

    return f"""
    <link rel='stylesheet' href='/static/style.css'>
    <h1>Welcome, {current_user.username}!</h1>
    <a href='/send_message_form'>Send Message</a> | <a href='/chat'>Live Chat</a> | <a href='/logout'>Logout</a>
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
    

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        login_user(user)  # Logs in the user
        return redirect(url_for("home"))
    else:
        return "Invalid credentials"   
    
    
@app.route("/login_form")
def login_form():
    return """
    <h2>Login</h2>
    <form action="/login" method="post">
        <label>Username:</label> <input type="text" name="username" required><br>
        <label>Password:</label> <input type="password" name="password" required><br>
        <button type="submit">Login</button>
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
@login_required
def send_message_form():
    users = User.query.all()
    user_options = "".join(f'<option value="{user.id}">{user.username}</option>' for user in users)

    return f"""
    <h2>Send a Private Message</h2>
    <form action="/send_message" method="post">
        <label>Sender:</label> 
        <input type="hidden" name="sender_id" value="{current_user.id}">
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

@app.route("/users")
def get_users():
    users = User.query.all()
    return {"users": [{"id": user.id, "username": user.username} for user in users]}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))


   
if __name__ == "__main__":
    socketio.run(app, debug=True)

