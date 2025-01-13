import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import psycopg2
from hvac import Client
from OpenSSL import crypto
import bcrypt  # Keep this if password hashing is used


# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Vault Initialization
vault_client = Client(url=os.getenv('VAULT_ADDR'), token=os.getenv('VAULT_TOKEN'))
vault_secrets = vault_client.secrets.database.generate_credentials(name='my-postgresql-role', mount_point='database')

# Fetch thresholds from Vault
def get_threshold_from_vault():
    try:
        result = vault_client.secrets.kv.read_secret_version(path='locomotive/thresholds', mount_point='secret')
        return result['data']['data']
    except Exception as e:
        return {'max_speed': 120, 'fuel_level_warning': 15, 'engine_temp_warning': 80}  # Default values

def get_locomotive_data_from_vault():
    try:
        # Fetch data from Vault (simulated data)
        result = vault_client.secrets.kv.read_secret_version(path='locomotive/data', mount_point='secret')
        return result['data']['data']
    except Exception as e:
        # Return default values if an error occurs or data is missing
        return {'speed': 100, 'fuel_level': 50, 'engine_temp': 70}

# PostgreSQL connection function
def get_db_connection():
    connection = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname='test',
        user=vault_secrets['data']['username'],
        password=vault_secrets['data']['password']
    )
    return connection

# Define User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(id=user_data[0], username=user_data[1])
    return None

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data and bcrypt.checkpw(password, user_data[2].encode('utf-8')):
            user = User(id=user_data[0], username=user_data[1])
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    locomotive_data = get_locomotive_data_from_vault()  # Fetch data from Vault
    thresholds = get_threshold_from_vault()  # Fetch threshold data from Vault
    
    # Check if data contains expected keys
    print(locomotive_data)  # Add this line to inspect the structure of locomotive_data
    
    return render_template('dashboard.html', 
                           username=current_user.username,
                           data=locomotive_data,  # Pass locomotive data
                           thresholds=thresholds)  # Pass threshold data

@app.route('/get_certificate')
def get_certificate():
    try:
        # Request a certificate from Vault's PKI engine
        cert = vault_client.secrets.pki.generate_certificate(
            name="locomotive-role",  # Role name configured in Vault
            common_name="www.locomotive-app.service.consul.com",  # Common name for the cert
        )
        
        # Extract certificate, private key, and issuer from Vault response
        certificate = cert['data']['certificate']
        private_key = cert['data']['private_key']
        issuer = cert['data']['issuing_ca']
        
        # Log the certificate issuance (optional but useful for debugging)
        #app.logger.info(f"Certificate issued for {cert['data']['common_name']} with TTL {cert['data']['ttl']}")
        
        # Return certificate and private key in the response
        return render_template('certificate.html', certificate=certificate, private_key=private_key, issuer=issuer)

    except Exception as e:
        # Log the error
        app.logger.error(f"Error while issuing certificate: {str(e)}")
        
        # Flash an error message to the user and redirect to the dashboard
        flash(f"Error while issuing certificate: {str(e)}", 'danger')
        return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            conn.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            conn.rollback()
            flash('Username already exists', 'danger')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080, ssl_context=("cert.crt", "private.key"))
