import os
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, current_app
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image
import json
from datetime import datetime
import math
from config import Config
from database import db, GoldRate, GST, Category, Product
from sqlalchemy import text  # Import text for raw SQL queries

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Ensure the Flask app has the secret key applied so sessions are signed
app.secret_key = app.config.get('SECRET_KEY')
# Ensure cookie defaults are set (development-friendly; change for production)
app.config.setdefault('SESSION_COOKIE_SECURE', app.config.get('SESSION_COOKIE_SECURE', False))
app.config.setdefault('SESSION_COOKIE_SAMESITE', app.config.get('SESSION_COOKIE_SAMESITE', 'Lax'))

# Configure logger
if not app.logger.handlers:
    logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

db.init_app(app)

# Create necessary directories
os.makedirs('static/uploads/categories', exist_ok=True)
os.makedirs('static/uploads/products', exist_ok=True)

# Admin credentials (in production, use environment variables)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or "admin"
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or "admin123"

def allowed_file(filename):
    # Use app.config for allowed extensions for consistency
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_IMAGE_EXTENSIONS']

def optimize_image(image_path, max_size=(800, 800)):
    """Optimize image size"""
    try:
        with Image.open(image_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(image_path, optimize=True, quality=85)
    except Exception as e:
        app.logger.warning(f"Image optimization error: {e}")

def calculate_price(weight, gold_rate, making_charge, gst_percentage):
    """Calculate final jewellery price"""
    metal_price = weight * gold_rate
    making_cost = weight * making_charge
    subtotal = metal_price + making_cost
    gst_amount = (subtotal * gst_percentage) / 100
    final_price = subtotal + gst_amount
    return math.ceil(final_price)

# Initialize database and default data
with app.app_context():
    try:
        db.create_all()
        app.logger.info("✅ Database tables created successfully!")

        # (optional) Initialize default data if not present
        # ... existing initialization logic ...
    except Exception as e:
        app.logger.error(f"Database initialization error: {e}")

@app.route('/')
def index():
    """Homepage"""
    try:
        gold_rate = GoldRate.query.order_by(GoldRate.updated_at.desc()).first()
        if not gold_rate:
            gold_rate = GoldRate(gold_22k=app.config.get('DEFAULT_GOLD_RATE', 6450.0),
                                 silver=app.config.get('DEFAULT_SILVER_RATE', 78.0))
            db.session.add(gold_rate)
            db.session.commit()
        
        categories = Category.query.all()
        
        return render_template('index.html',
                             shop_name=app.config.get('SHOP_NAME'),
                             shop_area=app.config.get('SHOP_AREA'),
                             shop_phone=app.config.get('SHOP_PHONE'),
                             shop_whatsapp=app.config.get('SHOP_WHATSAPP'),
                             gold_rate=gold_rate,
                             categories=categories)
    except Exception as e:
        app.logger.exception("Error loading homepage")
        return f"Error loading homepage: {str(e)}", 500

@app.route('/api/rates')
def get_rates():
    """Get current gold and silver rates"""
    try:
        gold_rate = GoldRate.query.order_by(GoldRate.updated_at.desc()).first()
        gst = GST.query.order_by(GST.updated_at.desc()).first()
        
        if not gold_rate:
            gold_rate = GoldRate(gold_22k=app.config.get('DEFAULT_GOLD_RATE', 6450.0),
                                 silver=app.config.get('DEFAULT_SILVER_RATE', 78.0))
            db.session.add(gold_rate)
            db.session.commit()
        
        if not gst:
            gst = GST(percentage=app.config.get('DEFAULT_GST', 3.0))
            db.session.add(gst)
            db.session.commit()
        
        return jsonify({
            'gold_22k': gold_rate.gold_22k,
            'silver': gold_rate.silver,
            'updated_at': gold_rate.updated_at.strftime('%I:%M %p'),
            'gst': gst.percentage
        })
    except Exception as e:
        app.logger.exception("Error in get_rates")
        return jsonify({'error': str(e)}), 500

# ... other routes unchanged, but consistent app.config usage applied throughout ...

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        app.logger.debug("Admin login attempt: username=%s", username)

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            app.logger.info("Admin logged in, session set")
            # After setting session, ensure we redirect to dashboard
            return redirect(url_for('admin_dashboard'))
        else:
            app.logger.debug("Admin login failed for username=%s", username)
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    app.logger.debug("Admin dashboard access, session admin_logged_in=%s", session.get('admin_logged_in'))
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        # Get counts
        categories_count = Category.query.count()
        products_count = Product.query.count()
        
        # Get latest rates
        gold_rate = GoldRate.query.order_by(GoldRate.updated_at.desc()).first()
        gst = GST.query.order_by(GST.updated_at.desc()).first()
        
        return render_template('admin/dashboard.html',
                             categories_count=categories_count,
                             products_count=products_count,
                             gold_rate=gold_rate,
                             gst=gst,
                             shop_name=app.config.get('SHOP_NAME'))
    except Exception as e:
        app.logger.exception("Admin dashboard error")
        return f"Admin dashboard error: {str(e)}", 500

# (The rest of the admin routes remain functionally the same but should use app.config where needed).