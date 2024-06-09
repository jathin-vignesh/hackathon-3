from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
import os
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)

# In a real application, you would use a database to store users and messages
USERS_FILE = os.path.join('data', 'users.json')
MESSAGES_FILE = os.path.join('data', 'messages.json')
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def load_messages():
    if not os.path.exists(MESSAGES_FILE):
        return {}
    with open(MESSAGES_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_messages(messages):
    with open(MESSAGES_FILE, 'w') as f:
        json.dump(messages, f)

def is_authenticated():
    return 'username' in session

def get_username():
    return session['username'] if is_authenticated() else None

@app.context_processor
def inject_user():
    return dict(is_authenticated=is_authenticated, get_username=get_username)

@app.route('/')
def index():
    if is_authenticated():
        username = get_username()
        messages = load_messages()
        new_message_count = sum(len(msg['messages']) for msg in messages.values() if msg['contact_info'] == username)
        return render_template('index.html', new_message_count=new_message_count)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users:
            return 'Username already exists. Please choose another one.'
        users[username] = password
        save_users(users)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('index'))
        return 'Invalid username or password.'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/report_lost', methods=['GET', 'POST'])
def report_lost():
    if not is_authenticated():
        return redirect(url_for('login'))
    if request.method == 'POST':
        item_name = request.form['item_name']
        location = request.form['location']
        contact_info = request.form['contact_info']
        photo = request.files['photo']
        if photo:
            photo_filename = photo.filename
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
        else:
            photo_filename = None
        messages = load_messages()
        messages[item_name] = {'location': location, 'contact_info': contact_info, 'reported_by': get_username(), 'photo': photo_filename, 'messages': []}
        save_messages(messages)
        return redirect(url_for('index'))
    return render_template('report_lost.html')

@app.route('/lost_items', methods=['GET', 'POST'])
def lost_items():
    if not is_authenticated():
        return redirect(url_for('login'))
    if request.method == 'POST':
        item_name = request.form['item_name']
        message = request.form['message']
        to_user = request.form['to_user'] 
        messages = load_messages()
        if item_name in messages:
            messages[item_name]['messages'].append({'from': get_username(), 'to': to_user, 'text': message})
        save_messages(messages)
        flash('Message sent successfully!', 'success')  
    messages = load_messages()
    return render_template('lost_items.html', lost_items=messages)


@app.route('/inbox')
def inbox():
    if not is_authenticated():
        return redirect(url_for('login'))
    username = get_username()
    messages = load_messages()
    user_messages = {}
    for item_name, msg_data in messages.items():
        for msg in msg_data['messages']:
            if msg['to'] == username:
                if item_name not in user_messages:
                    user_messages[item_name] = []
                user_messages[item_name].append(msg)
    return render_template('inbox.html', messages=user_messages)


@app.route('/search_lost', methods=['GET', 'POST'])
def search_lost():
    if not is_authenticated():
        return redirect(url_for('login'))
    if request.method == 'POST':
        keyword = request.form['keyword'].lower()
        messages = load_messages()
        filtered_messages = {item_name: msg for item_name, msg in messages.items() if keyword in item_name.lower()}
        return render_template('search_results.html', results=filtered_messages)
    return render_template('search_lost.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
