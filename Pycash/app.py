from flask import Flask, render_template, url_for, flash, redirect, request, Response, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from forms import LoginForm, ForgetPasswordForm, SignUpForm
from flask_sqlalchemy import SQLAlchemy
from models import User, db
from flask_session import Session
import sqlite3
import cv2
import threading
from deepface import DeepFace
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.secret_key = 'supersecretkey'
Session(app)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
db.init_app(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = "login"

def get_user_by_id(user_id):
    with sqlite3.connect('login.db') as conn:
        curs = conn.cursor()
        curs.execute("SELECT * FROM login WHERE user_id = ?", (user_id,))
        return curs.fetchone()

# Video and face matching globals
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
face_match = False
reference_img_path = "static/img/reference.jpg"
reference_img = cv2.imread(reference_img_path)

if reference_img is None:
    raise FileNotFoundError(f"Reference image not found at '{reference_img_path}'")

# Convert to RGB and resize for DeepFace
reference_img = cv2.cvtColor(reference_img, cv2.COLOR_BGR2RGB)
reference_img = cv2.resize(reference_img, (224, 224))
lock = threading.Lock()

# Flask User model
class User(UserMixin):
    def __init__(self, user_id, username, email, password,photo, is_admin=False):
        self.id = str(user_id)  # user_id is passed as the first argument
        self.username = username
        self.email = email
        self.password = password 
        self.photo = photo
        self.is_admin = bool(is_admin)  # Ensures is_admin is a boolean value

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id



@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect('login.db') as conn:
        curs = conn.cursor()
        curs.execute("SELECT * FROM login WHERE user_id = ?", [user_id])
        user = curs.fetchone()
        
        print(user)  # Debugging: Print the result to see the structure of the returned data
        
        if user:
            return User(user[0], user[1], user[2], user[3], user[4], user[5])  # Assuming user[3] is password
    return None



# Helper function for database operations
def get_user_by_email(email):
    with sqlite3.connect('login.db') as conn:
        curs = conn.cursor()
        curs.execute("SELECT * FROM login WHERE email = ?", [email])
        return curs.fetchone()

# Face verification logic
def check_face(frame):
    """Check if the face matches the reference image."""
    global face_match
    try:
        # Preprocess the frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (224, 224))  # Resize for DeepFace

        # Perform face verification
        result = DeepFace.verify(frame_resized, reference_img.copy())
        with lock:
            face_match = result['verified']
    except ValueError as e:
        print("Error in face verification:", e)
        with lock:
            face_match = False

def generate_frames():
    """Generate video frames with face match status."""
    global face_match
    counter = 0
    while True:
        success, frame = cap.read()
        if not success:
            break

        # Run face verification every 30 frames
        if counter % 30 == 0:
            threading.Thread(target=check_face, args=(frame.copy(),)).start()
        counter += 1

        # Add match status text on the frame
        with lock:
            if face_match:
                cv2.putText(frame, "Match", (20, 450), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "No Match", (20, 450), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 2)

        # Encode frame for streaming
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/', methods=['GET', 'POST'])
def index():
    form = LoginForm()
    forget_form = ForgetPasswordForm()
    sign_up_form = SignUpForm()

        # Sign Up form submission
    if sign_up_form.validate_on_submit() and request.form['action'] == 'sign_up':
        user = get_user_by_email(sign_up_form.email.data)
        if user:
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for('index'))
        
        # Determine if the user wants to register as admin
        is_admin = 1 if 'is_admin' in request.form and request.form['is_admin'] == '1' else 0  # Check if admin checkbox is selected
        
        # Add user into the database with is_admin field
        with sqlite3.connect('login.db') as conn:
            curs = conn.cursor()
            curs.execute("INSERT INTO login (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
                        [sign_up_form.username.data, 
                        sign_up_form.email.data, 
                        sign_up_form.password.data, 
                        is_admin])  # Set admin flag based on input
            conn.commit()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('dashboard'))  # Redirect to registered page


    # Handle Forget Password form submission
    if forget_form.validate_on_submit() and request.form['action'] == 'forget_password':
        user = get_user_by_email(forget_form.email.data)
        if user:
            flash("Password reset link has been sent to your email.", "success")
        else:
            flash("Email not found.", "danger")

    # Handle Login form submission
    if form.validate_on_submit() and request.form.get('action') == 'login':
        # Strip whitespace from the email and password inputs
        email_input = form.email.data.strip()
        password_input = form.password.data.strip()

        print(f"Attempting login with Email: '{email_input}' and Password: '{password_input}'")  # Debugging line

        # Retrieve user by email
        user = get_user_by_email(email_input)

        # If user exists
        if user:
            print(f"User found: {user}")  # Debugging line
            stored_password = user[3]  # Password column is user[3]
            print(f"Stored password: {stored_password}")  # Debugging line

            # Check password match
            if stored_password == password_input:
                print("Password match!")  # Debugging line
                user_obj = User(user[0], user[1], user[2], user[3], user[4], user[5])  # Add the email (user[2]) and password (user[3]) correctly
                login_user(user_obj, remember=form.remember.data)
                flash(f"Logged in successfully, {email_input.split('@')[0]}!", 'success')
                print("Login successful, redirecting to dashboard...")  # Debugging line
                return redirect(url_for('dashboard'))  # Redirect to dashboard after successful login
            else:
                print(f"Password mismatch: '{password_input}' != '{stored_password}'")  # Debugging line
                flash("Login unsuccessful. Incorrect password.", "danger")  # Incorrect password
        else:
            print(f"No user found with email: '{email_input}'")  # Debugging line
            flash("Login unsuccessful. No user found with that email.", "danger")  # User not found

    return render_template('index.html', title="Login", form=form, forget_form=forget_form, sign_up_form=sign_up_form)



@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Get the user input from the form
        new_username = request.form['username']
        new_email = request.form['email']
        new_password = request.form['password']
        photo = request.files.get('photo')

        # Handle photo upload
        if photo and allowed_file(photo.filename):
            filename = secure_filename(new_username + '.' + photo.filename.rsplit('.', 1)[1])
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Update photo path in the database for the current user (based on username)
            with sqlite3.connect('login.db') as conn:
                curs = conn.cursor()
                curs.execute("UPDATE login SET photo = ? WHERE username = ?", 
                             (filename, current_user.username))  # Using the logged-in user's username
                conn.commit()

        # Update other user info in the database
        with sqlite3.connect('login.db') as conn:
            curs = conn.cursor()
            curs.execute("UPDATE login SET username = ?, email = ?, password = ? WHERE username = ?",
                         (new_username, new_email, new_password, current_user.username))  # Using username
            conn.commit()

        flash("Your profile has been updated!", "success")
        return redirect(url_for('profile'))  # Redirect to the same page to reflect changes

    return render_template('profile.html')
@app.route('/usermanagement', methods=['GET', 'POST'])
@login_required
def user_management():
    # Ensure only admins can access this page
    if not getattr(current_user, 'is_admin', False):  # Safeguard in case 'is_admin' is missing
        flash("You do not have permission to view this page.", "danger")
        return redirect(url_for('user_management'))  # Redirect to a safe page (dashboard)

    try:
        # Connect to the database and fetch user data
        with sqlite3.connect('login.db') as conn:
            conn.row_factory = sqlite3.Row  # Allows dictionary-like access to rows
            curs = conn.cursor()
            curs.execute("SELECT * FROM login")  # Fetch all user records
            users = curs.fetchall()
    except sqlite3.Error as e:
        flash(f"Database error: {str(e)}", "danger")  # Display error if query fails
        users = []  # Default empty list to avoid template errors

    # Render the User Management template and pass users
    return render_template('usermanagement.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    # Only allow admins to delete users
    if not current_user.is_admin:
        flash("You do not have permission to delete users.", "danger")
        return redirect(url_for('dashboard'))

    # Delete the user from the database
    try:
        with sqlite3.connect('login.db') as conn:
            curs = conn.cursor()
            curs.execute("DELETE FROM login WHERE user_id = ?", (user_id,))
            conn.commit()
        flash("User deleted successfully.", "success")
    except Exception as e:
        flash("An error occurred while deleting the user. Please try again.", "danger")
    
    return redirect(url_for('user_management'))


@app.route('/registered')
def registered():
    return render_template('registered.html')  # Render the registered page extending base.html

@app.route('/dashboard')
@login_required  # Make sure the user is logged in before accessing the dashboard
def dashboard():
    username = session.get('username', 'Guest')
    return render_template('dashboard.html', username=username)

def get_user_by_email(email):
    with sqlite3.connect('login.db') as conn:
        curs = conn.cursor()
        curs.execute("SELECT * FROM login WHERE email = ?", [email])
        return curs.fetchone()

# Route to upload a profile photo
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_photo', methods=['POST'])
@login_required  # Ensure the user is logged in before uploading
def upload_photo():
    # Get the username of the current logged-in user
    username = current_user.username

    # Check if the photo is part of the request
    if 'photo' not in request.files:
        flash('No file uploaded!', 'danger')
        return redirect(url_for('profile'))  # Redirect back to profile

    file = request.files['photo']
    if file.filename == '':
        flash('No selected file!', 'danger')
        return redirect(url_for('profile'))  # Redirect back to profile

    # Ensure the file is allowed
    if file and allowed_file(file.filename):
        # Create a secure filename for the uploaded file
        filename = secure_filename(username + '.' + file.filename.rsplit('.', 1)[1].lower())
        
        # Save the file in the 'uploads' folder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Update the user's profile photo in the database
        with sqlite3.connect('login.db') as conn:
            curs = conn.cursor()
            curs.execute("UPDATE login SET photo = ? WHERE username = ?", (filename, username))
            conn.commit()

        flash('Profile photo uploaded successfully!', 'success')
        return redirect(url_for('profile'))  # Redirect back to profile

    flash('Failed to upload photo. Please try again.', 'danger')
    return redirect(url_for('profile'))  # Redirect back to profile

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

@app.route('/video_feed')
@login_required
def video_feed():
    """Stream the video feed."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/check_match_status')
@login_required
def check_match_status():
    """Return the face match status as JSON."""
    global face_match
    with lock:
        return jsonify({"face_match": face_match})

@app.route('/face_cash', methods=['GET', 'POST'])
@login_required
def face_cash():
    total_price = request.args.get('total_price', 0)

    # If the face match is successful, process the order
    if request.method == 'POST':
        global face_match
        with lock:
            if face_match:
                return redirect(url_for('payment_success'))
            else:
                flash("Face verification failed. Please try again.", "danger")
                return redirect(url_for('face_cash', total_price=total_price))
    return render_template('face_cash.html', total_price=total_price)

@app.route('/payment_success')
@login_required
def payment_success():
    items = session.get('cart', [])  # Retrieve items from session
    total_price = session.get('total_price', 0.0)  # Retrieve total price from session

    if not items or total_price == 0.0:
        return redirect(url_for('index'))  # If no items or total price is 0, redirect to the home page

    # Render the payment success page with the items and total price
    return render_template('payment_success.html', items=items, total_price=total_price)

#shopppeeeeeeeeeeeee
products = [
    {'id': 1, 'name': 'Graphics Card', 'price': 500.0, 'image_url': '../static/img/graphics_card.png'},
    {'id': 2, 'name': 'Keyboard', 'price': 300.0, 'image_url': '../static/img/keyboard.png'},
    {'id': 3, 'name': 'Power Supply', 'price': 100.0, 'image_url': '../static/img/power.png'},
    {'id': 4, 'name': 'Motherboard', 'price': 200.0, 'image_url': '../static/img/motherboard.png'},
    {'id': 5, 'name': 'RAM (16GB)', 'price': 150.0, 'image_url': '../static/img/ram.png'},
    {'id': 6, 'name': 'SSD (1TB)', 'price': 120.0, 'image_url': '../static/img/ssd.png'},
]

cart = []

@app.route('/sshop')
def shop():
    return render_template('shop.html', products=products)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        total_price = sum(item['price'] for item in cart)  # Calculate total price

        if not name or not address:
            return "Please fill in all fields", 400

        # Store cart and total price in the session before redirecting
        session['cart'] = cart
        session['total_price'] = total_price

        # Redirect to face-cash for payment verification
        return redirect(url_for('face_cash', total_price=total_price))

    # Render the checkout page
    total_price = sum(item['price'] for item in cart)
    return render_template('checkout.html', cart=cart, total_price=total_price)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    product = next((p for p in products if p['id'] == product_id), None)
    if product:
        cart.append(product)
    return redirect(url_for('shop'))

team_members = [
    {
        'name': 'Rigel Parco',
        'role': 'Project Manager & Developer',
        'image': 'rigel_parco.jpg',
        'description': 'Rigel is the driving force behind the project, coordinating efforts and ensuring that everything stays on track.'
    },
    {
        'name': 'Leo Tagum',
        'role': 'Lead Developer',
        'image': 'leo_tagum.jpg',
        'description': 'Leo is the lead developer, handling the core code, backend systems, and ensuring smooth technical performance.'
    },
    {
        'name': 'Caren Epress',
        'role': 'UI/UX Designer',
        'image': 'caren_epress.jpg',
        'description': 'Caren designs the user interface and experience, ensuring the application is intuitive and visually appealing.'
    }
]

@app.route('/about_us')
def about_us():
    return render_template('about.html', team_members=team_members)

if __name__ == "__main__":
    app.run(debug=True)
