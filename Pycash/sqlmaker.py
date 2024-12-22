import sqlite3

# Helper function to get a user by email
def get_user_by_email(email):
    with sqlite3.connect('login.db') as conn:
        curs = conn.cursor()
        curs.execute("SELECT * FROM login WHERE email = ?", [email])
        return curs.fetchone()

# Function to check user login
def check_login(email_input, password_input):
    # Retrieve user by email
    user = get_user_by_email(email_input)

    # If user exists
    if user:
        print(f"User found: {user}")  # Debugging line
        # Compare passwords (the actual password is in index 3, not 2)
        if user[3] == password_input:  # Correct column for password
            print("Password match!")  # Debugging line
            return True  # Successful login
        else:
            print(f"Password mismatch: {password_input} != {user[3]}")  # Debugging line
            return False  # Incorrect password
    else:
        print("No user found with that email.")  # Debugging line
        return False  # User not found

if __name__ == "__main__":
    # Get email and password input from the user
    email_input = input("Enter your email: ").strip()
    password_input = input("Enter your password: ").strip()

    # Check login
    if check_login(email_input, password_input):
        print("Login successful!")
    else:
        print("Login unsuccessful. Please check your email and password.")
