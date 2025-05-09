from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_socketio import join_room, emit
from flask_login import current_user
from werkzeug.utils import secure_filename
from flask_moment import Moment
import json
from pywebpush import webpush, WebPushException
import os

from forms import ProfileUpdateForm  # make sure this exists

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app)
moment = Moment(app)

# -------------------------------
# MODELS
# -------------------------------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bio = db.Column(db.String(500))
    profile_picture = db.Column(db.String(120), default='default.jpg')
    
    # Additional profile fields
    full_name = db.Column(db.String(150))
    location = db.Column(db.String(100))
    website = db.Column(db.String(200))
    birthdate = db.Column(db.Date)

    # Relationships
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------------------
# LOGIN MANAGER
# -------------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------------
# ROUTES
# -------------------------------

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('home.html', users=users)

@app.route('/chat/<int:user_id>', methods=['GET', 'POST'])
@login_required
def chat(user_id):
    partner = User.query.get_or_404(user_id)

    if request.method == 'POST':
        content = request.form.get('message')
        if content:
            message = Message(sender_id=current_user.id, receiver_id=partner.id, content=content)
            db.session.add(message)
            db.session.commit()
            return redirect(url_for('chat', user_id=partner.id))

    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == partner.id)) |
        ((Message.sender_id == partner.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp).all()

    return render_template('chat.html', partner=partner, messages=messages)



@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileUpdateForm()
    if form.validate_on_submit():
        current_user.bio = form.bio.data

        if form.profile_picture.data:
            picture_file = form.profile_picture.data
            filename = secure_filename(picture_file.filename)
            picture_path = os.path.join(app.root_path, 'static/profile_pics', filename)
            picture_file.save(picture_path)
            current_user.profile_picture = filename

        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('profile'))

    form.bio.data = current_user.bio
    return render_template('profile.html', form=form, user=current_user)


# Handle incoming messages
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

        # Emit the new message to both the sender and receiver
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

# Handle user connection
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(f'user_{current_user.id}')
        print(f'{current_user.username} joined room user_{current_user.id}')

# Handle typing status
@socketio.on('typing')
def handle_typing(data):
    if not current_user.is_authenticated:
        return  # Ignore if the user is not logged in

    receiver_id = data.get('receiver_id')
    if receiver_id:
        # Emit the typing event to the receiver
        emit('typing', {
            'sender_id': current_user.id,
            'receiver_id': receiver_id
        }, room=f'user_{receiver_id}')
        
        
# VAPID keys (replace with your actual keys)
VAPID_PRIVATE_KEY = '<MHcCAQEEIIByw1v+8MMyBwUvPRr+yvZGI884U6sKU4qzjEWv1RW9oAoGCCqGSM49AwEHoUQDQgAE8fNs9ns7oOhS45NZtLHzrvsDAxuslAwLeRxegjZAd0ga3efURDrkgki7k7GoKQEs3JeQjDW97xpkHEt3cS9LqQ==>'
VAPID_PUBLIC_KEY = '<MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE8fNs9ns7oOhS45NZtLHzrvsDAxuslAwLeRxegjZAd0ga3efURDrkgki7k7GoKQEs3JeQjDW97xpkHEt3cS9LqQ==>'

# Function to send a push notification
def send_push_notification(subscription_info, message):
    try:
        # Send push notification using pywebpush
        webpush(
            subscription_info,
            data=json.dumps({
                "title": "New Message",
                "body": message,
                "icon": "/static/icons/notification-icon.png",  # Update with your actual path
                "badge": "/static/icons/notification-badge.png"  # Update with your actual path
            }),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_public_key=VAPID_PUBLIC_KEY,
            ttl=24 * 60 * 60  # Time to live: 24 hours
        )
    except WebPushException as e:
        print("Error sending push notification:", e)

# Route to handle sending push notifications
@app.route('/send_push_notification', methods=['POST'])
def send_notification():
    data = request.get_json()
    subscription_info = data['subscription_info']
    message = data['message']
    
    # Call the function to send the notification
    send_push_notification(subscription_info, message)

    return jsonify({"status": "Notification sent"})       

# -------------------------------
# RUN APP
# -------------------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
