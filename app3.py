from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_cors import CORS
import os
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

db.init_app(app)

# Create necessary directories
os.makedirs('static/uploads/categories', exist_ok=True)
os.makedirs('static/uploads/products', exist_ok=True)

# Admin credentials (in production, use environment variables)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_IMAGE_EXTENSIONS']

def optimize_image(image_path, max_size=(800, 800)):
    """Optimize image size"""
    try:
        with Image.open(image_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(image_path, optimize=True, quality=85)
    except Exception as e:
        print(f"Image optimization error: {e}")

def calculate_price(weight, gold_rate, making_charge, gst_percentage):
    """Calculate final jewellery price"""
    metal_price = weight * gold_rate
    making_cost = weight * making_charge
    subtotal = metal_price + making_cost
    gst_amount = (subtotal * gst_percentage) / 100
    final_price = subtotal + gst_amount
    return math.ceil(final_price)

# Initialize database and create tables
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created successfully!")
        
        # Check if default data exists
        if GoldRate.query.count() == 0:
            default_rate = GoldRate(gold_22k=6450, silver=78)
            db.session.add(default_rate)
            print("✅ Default gold rate added!")
        
        if GST.query.count() == 0:
            default_gst = GST(percentage=3.0)
            db.session.add(default_gst)
            print("✅ Default GST added!")
        
        if Category.query.count() == 0:
            # Add default categories
            default_categories = [
                Category(name="Ring", name_bn="রিং", image=None),
                Category(name="Chain", name_bn="চেইন", image=None),
                Category(name="Necklace", name_bn="হার", image=None),
                Category(name="Bangle", name_bn="চুড়ি", image=None),
                Category(name="Silver Items", name_bn="সিলভার আইটেম", image=None)
            ]
            db.session.add_all(default_categories)
            print("✅ Default categories added!")
        
        db.session.commit()
        print("✅ All default data initialized!")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        db.session.rollback()

@app.route('/')
def index():
    """Homepage"""
    try:
        gold_rate = GoldRate.query.order_by(GoldRate.updated_at.desc()).first()
        if not gold_rate:
            gold_rate = GoldRate(gold_22k=6450, silver=78)
            db.session.add(gold_rate)
            db.session.commit()
        
        categories = Category.query.all()
        
        return render_template('index.html',
                             shop_name=Config.SHOP_NAME,
                             shop_area=Config.SHOP_AREA,
                             shop_phone=Config.SHOP_PHONE,
                             shop_whatsapp=Config.SHOP_WHATSAPP,
                             gold_rate=gold_rate,
                             categories=categories)
    except Exception as e:
        return f"Error loading homepage: {str(e)}", 500

@app.route('/api/rates')
def get_rates():
    """Get current gold and silver rates"""
    try:
        gold_rate = GoldRate.query.order_by(GoldRate.updated_at.desc()).first()
        gst = GST.query.order_by(GST.updated_at.desc()).first()
        
        if not gold_rate:
            gold_rate = GoldRate(gold_22k=Config.DEFAULT_GOLD_RATE, silver=Config.DEFAULT_SILVER_RATE)
            db.session.add(gold_rate)
            db.session.commit()
        
        if not gst:
            gst = GST(percentage=Config.DEFAULT_GST)
            db.session.add(gst)
            db.session.commit()
        
        return jsonify({
            'gold_22k': gold_rate.gold_22k,
            'silver': gold_rate.silver,
            'updated_at': gold_rate.updated_at.strftime('%I:%M %p'),
            'gst': gst.percentage
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories')
def get_categories():
    """Get all categories"""
    try:
        categories = Category.query.all()
        return jsonify([cat.to_dict() for cat in categories])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products')
def get_products():
    """Get all products"""
    try:
        category_id = request.args.get('category_id')
        
        if category_id:
            products = Product.query.filter_by(category_id=category_id).all()
        else:
            products = Product.query.all()
        
        gold_rate = GoldRate.query.order_by(GoldRate.updated_at.desc()).first()
        gst = GST.query.order_by(GST.updated_at.desc()).first()
        
        product_list = []
        for product in products:
            product_dict = product.to_dict()
            
            # Calculate price
            if gold_rate and gst:
                price = calculate_price(
                    product.weight,
                    gold_rate.gold_22k,
                    product.making_charge,
                    gst.percentage
                )
                product_dict['calculated_price'] = price
            
            product_list.append(product_dict)
        
        return jsonify(product_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Product detail page"""
    try:
        product = Product.query.get_or_404(product_id)
        gold_rate = GoldRate.query.order_by(GoldRate.updated_at.desc()).first()
        gst = GST.query.order_by(GST.updated_at.desc()).first()
        
        # Calculate price
        price = 0
        if gold_rate and gst:
            price = calculate_price(
                product.weight,
                gold_rate.gold_22k,
                product.making_charge,
                gst.percentage
            )
        
        return render_template('product.html',
                             product=product,
                             calculated_price=price,
                             shop_name=Config.SHOP_NAME,
                             shop_phone=Config.SHOP_PHONE,
                             shop_whatsapp=Config.SHOP_WHATSAPP)
    except Exception as e:
        return f"Error loading product: {str(e)}", 500

# Serve uploaded files
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)

# ========== ADMIN ROUTES ==========

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard"""
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
                             shop_name=Config.SHOP_NAME)
    except Exception as e:
        return f"Admin dashboard error: {str(e)}", 500

@app.route('/admin/rates', methods=['GET', 'POST'])
def admin_rates():
    """Manage gold/silver rates and GST"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            
            if action == 'update_rates':
                gold_22k = float(request.form.get('gold_22k'))
                silver = float(request.form.get('silver'))
                
                new_rate = GoldRate(gold_22k=gold_22k, silver=silver)
                db.session.add(new_rate)
                db.session.commit()
                
                return redirect(url_for('admin_rates'))
            
            elif action == 'update_gst':
                gst_percentage = float(request.form.get('gst_percentage'))
                
                new_gst = GST(percentage=gst_percentage)
                db.session.add(new_gst)
                db.session.commit()
                
                return redirect(url_for('admin_rates'))
        except Exception as e:
            return f"Error updating rates: {str(e)}", 500
    
    try:
        gold_rate = GoldRate.query.order_by(GoldRate.updated_at.desc()).first()
        gst = GST.query.order_by(GST.updated_at.desc()).first()
        
        return render_template('admin/rates.html', 
                             gold_rate=gold_rate, 
                             gst=gst,
                             shop_name=Config.SHOP_NAME)
    except Exception as e:
        return f"Error loading rates page: {str(e)}", 500

@app.route('/admin/categories', methods=['GET', 'POST'])
def admin_categories():
    """Manage categories"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            
            if action == 'add':
                name = request.form.get('name')
                name_bn = request.form.get('name_bn')
                image = request.files.get('image')
                
                category = Category(name=name, name_bn=name_bn)
                
                if image and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    image_path = f'static/uploads/categories/{unique_filename}'
                    image.save(image_path)
                    optimize_image(image_path)
                    category.image = f'uploads/categories/{unique_filename}'
                
                db.session.add(category)
                db.session.commit()
                
            elif action == 'edit':
                category_id = int(request.form.get('category_id'))
                name = request.form.get('name')
                name_bn = request.form.get('name_bn')
                image = request.files.get('image')
                
                category = Category.query.get(category_id)
                if category:
                    category.name = name
                    category.name_bn = name_bn
                    
                    if image and allowed_file(image.filename):
                        # Delete old image if exists
                        if category.image and os.path.exists(f'static/{category.image}'):
                            os.remove(f'static/{category.image}')
                        
                        filename = secure_filename(image.filename)
                        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                        image_path = f'static/uploads/categories/{unique_filename}'
                        image.save(image_path)
                        optimize_image(image_path)
                        category.image = f'uploads/categories/{unique_filename}'
                    
                    db.session.commit()
            
            elif action == 'delete':
                category_id = int(request.form.get('category_id'))
                category = Category.query.get(category_id)
                if category:
                    # Delete associated image
                    if category.image and os.path.exists(f'static/{category.image}'):
                        os.remove(f'static/{category.image}')
                    
                    db.session.delete(category)
                    db.session.commit()
            
            return redirect(url_for('admin_categories'))
            
        except Exception as e:
            return f"Error managing categories: {str(e)}", 500
    
    try:
        categories = Category.query.all()
        return render_template('admin/categories.html', 
                             categories=categories,
                             shop_name=Config.SHOP_NAME)
    except Exception as e:
        return f"Error loading categories: {str(e)}", 500

@app.route('/admin/products', methods=['GET', 'POST'])
def admin_products():
    """Manage products"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            
            if action == 'add':
                name = request.form.get('name')
                name_bn = request.form.get('name_bn')
                description_bn = request.form.get('description_bn')
                category_id = int(request.form.get('category_id'))
                purity = request.form.get('purity')
                weight = float(request.form.get('weight'))
                making_charge = float(request.form.get('making_charge'))
                stock_status = request.form.get('stock_status')
                
                # Handle multiple images
                image_paths = []
                for i in range(1, 4):  # Max 3 images
                    image = request.files.get(f'image_{i}')
                    if image and allowed_file(image.filename):
                        filename = secure_filename(image.filename)
                        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}_{filename}"
                        image_path = f'static/uploads/products/{unique_filename}'
                        image.save(image_path)
                        optimize_image(image_path)
                        image_paths.append(f'uploads/products/{unique_filename}')
                
                product = Product(
                    name=name,
                    name_bn=name_bn,
                    description_bn=description_bn,
                    category_id=category_id,
                    purity=purity,
                    weight=weight,
                    making_charge=making_charge,
                    stock_status=stock_status,
                    images=','.join(image_paths) if image_paths else None
                )
                
                db.session.add(product)
                db.session.commit()
                
            elif action == 'edit':
                product_id = int(request.form.get('product_id'))
                product = Product.query.get(product_id)
                
                if product:
                    product.name = request.form.get('name')
                    product.name_bn = request.form.get('name_bn')
                    product.description_bn = request.form.get('description_bn')
                    product.category_id = int(request.form.get('category_id'))
                    product.purity = request.form.get('purity')
                    product.weight = float(request.form.get('weight'))
                    product.making_charge = float(request.form.get('making_charge'))
                    product.stock_status = request.form.get('stock_status')
                    
                    db.session.commit()
            
            elif action == 'delete':
                product_id = int(request.form.get('product_id'))
                product = Product.query.get(product_id)
                if product:
                    # Delete associated images
                    if product.images:
                        for img_path in product.images.split(','):
                            if img_path.strip() and os.path.exists(f'static/{img_path.strip()}'):
                                os.remove(f'static/{img_path.strip()}')
                    
                    db.session.delete(product)
                    db.session.commit()
            
            return redirect(url_for('admin_products'))
            
        except Exception as e:
            return f"Error managing products: {str(e)}", 500
    
    try:
        categories = Category.query.all()
        products = Product.query.all()
        
        # Calculate prices for display
        gold_rate = GoldRate.query.order_by(GoldRate.updated_at.desc()).first()
        gst = GST.query.order_by(GST.updated_at.desc()).first()
        
        product_list = []
        for product in products:
            product_dict = product.to_dict()
            
            if gold_rate and gst:
                price = calculate_price(
                    product.weight,
                    gold_rate.gold_22k,
                    product.making_charge,
                    gst.percentage
                )
                product_dict['calculated_price'] = price
            
            product_list.append(product_dict)
        
        return render_template('admin/products.html',
                             categories=categories,
                             products=product_list,
                             shop_name=Config.SHOP_NAME)
    except Exception as e:
        return f"Error loading products: {str(e)}", 500

# API endpoints for admin
@app.route('/api/admin/update-rates', methods=['POST'])
def api_update_rates():
    """API to update rates"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        new_rate = GoldRate(
            gold_22k=float(data['gold_22k']),
            silver=float(data['silver'])
        )
        db.session.add(new_rate)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/update-gst', methods=['POST'])
def api_update_gst():
    """API to update GST"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        new_gst = GST(percentage=float(data['gst_percentage']))
        db.session.add(new_gst)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/products', methods=['GET'])
def api_get_all_products():
    """API to get all products for admin"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        products = Product.query.all()
        return jsonify([product.to_dict() for product in products])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/products/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    """API to delete product"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        product = Product.query.get_or_404(product_id)
        
        # Delete associated images
        if product.images:
            for img_path in product.images.split(','):
                if img_path.strip() and os.path.exists(f'static/{img_path.strip()}'):
                    os.remove(f'static/{img_path.strip()}')
        
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("=" * 50)
    print("মানালী জুয়েলার্স ওয়েবসাইট")
    print("=" * 50)
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Shop: {Config.SHOP_NAME}")
    print(f"Area: {Config.SHOP_AREA}")
    print("=" * 50)
    
    # Test database connection
    with app.app_context():
        try:
            db.session.execute(text('SELECT 1'))
            print("✅ Database connection successful!")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print("\nTroubleshooting steps:")
            print("1. Make sure Mariadb is running: mysqld_safe &")
            print("2. Check database credentials in config.py")
            print("3. Verify database exists: mysql -u root -e 'SHOW DATABASES;'")
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
