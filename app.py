from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from PIL import Image
import json
from datetime import datetime
from config import Config
from database import db, GoldRate, GST, Category, Product
import math

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

db.init_app(app)

# Create upload directories
os.makedirs('static/uploads/categories', exist_ok=True)
os.makedirs('static/uploads/products', exist_ok=True)

# Admin credentials (in production, use environment variables)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_IMAGE_EXTENSIONS

def optimize_image(image_path, max_size=(800, 800)):
    """Optimize image size"""
    try:
        with Image.open(image_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(image_path, optimize=True, quality=85)
    except Exception as e:
        print(f"Error optimizing image: {e}")

def calculate_price(weight, gold_rate, making_charge, gst_percentage):
    """Calculate final jewellery price"""
    metal_price = weight * gold_rate
    making_cost = weight * making_charge
    subtotal = metal_price + making_cost
    gst_amount = (subtotal * gst_percentage) / 100
    final_price = subtotal + gst_amount
    return math.ceil(final_price)

@app.route('/')
def index():
    """Homepage"""
    gold_rate = GoldRate.query.order_by(GoldRate.updated_at.desc()).first()
    if not gold_rate:
        gold_rate = GoldRate(gold_22k=Config.DEFAULT_GOLD_RATE, silver=Config.DEFAULT_SILVER_RATE)
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

@app.route('/api/rates')
def get_rates():
    """Get current gold and silver rates"""
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

@app.route('/api/categories')
def get_categories():
    """Get all categories"""
    categories = Category.query.all()
    return jsonify([cat.to_dict() for cat in categories])

@app.route('/api/products')
def get_products():
    """Get all products"""
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

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Product detail page"""
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
                         gst=gst)

@app.route('/admin/rates', methods=['GET', 'POST'])
def admin_rates():
    """Manage gold/silver rates and GST"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_rates':
            gold_22k = float(request.form.get('gold_22k'))
            silver = float(request.form.get('silver'))
            
            new_rate = GoldRate(gold_22k=gold_22k, silver=silver)
            db.session.add(new_rate)
            db.session.commit()
            
        elif action == 'update_gst':
            gst_percentage = float(request.form.get('gst_percentage'))
            
            new_gst = GST(percentage=gst_percentage)
            db.session.add(new_gst)
            db.session.commit()
    
    gold_rate = GoldRate.query.order_by(GoldRate.updated_at.desc()).first()
    gst = GST.query.order_by(GST.updated_at.desc()).first()
    
    return render_template('admin/rates.html', gold_rate=gold_rate, gst=gst)

@app.route('/admin/categories', methods=['GET', 'POST'])
def admin_categories():
    """Manage categories"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name')
            name_bn = request.form.get('name_bn')
            image = request.files.get('image')
            
            category = Category(name=name, name_bn=name_bn)
            
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = f'static/uploads/categories/{filename}'
                image.save(image_path)
                optimize_image(image_path)
                category.image = f'uploads/categories/{filename}'
            
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
                    filename = secure_filename(image.filename)
                    image_path = f'static/uploads/categories/{filename}'
                    image.save(image_path)
                    optimize_image(image_path)
                    category.image = f'uploads/categories/{filename}'
                
                db.session.commit()
            
        elif action == 'delete':
            category_id = int(request.form.get('category_id'))
            category = Category.query.get(category_id)
            if category:
                db.session.delete(category)
                db.session.commit()
    
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/products', methods=['GET', 'POST'])
def admin_products():
    """Manage products"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
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
                    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}_{secure_filename(image.filename)}"
                    image_path = f'static/uploads/products/{filename}'
                    image.save(image_path)
                    optimize_image(image_path)
                    image_paths.append(f'uploads/products/{filename}')
            
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
                db.session.delete(product)
                db.session.commit()
    
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
                         products=product_list)

# API endpoints for admin
@app.route('/api/admin/update-rates', methods=['POST'])
def api_update_rates():
    """API to update rates"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    new_rate = GoldRate(
        gold_22k=float(data['gold_22k']),
        silver=float(data['silver'])
    )
    db.session.add(new_rate)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/admin/update-gst', methods=['POST'])
def api_update_gst():
    """API to update GST"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    new_gst = GST(percentage=float(data['gst_percentage']))
    db.session.add(new_gst)
    db.session.commit()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Initialize default data
        if not GoldRate.query.first():
            db.session.add(GoldRate(gold_22k=6450, silver=78))
        
        if not GST.query.first():
            db.session.add(GST(percentage=3.0))
        
        db.session.commit()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
