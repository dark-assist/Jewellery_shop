import os
from datetime import datetime

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'jewellery-shop-secret-key-2024'
    
    # Mariadb configuration for Termux
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://jewellery_user:jewellery_pass123@localhost/jewellery_shop'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_TIMEOUT = 30
    SQLALCHEMY_POOL_RECYCLE = 3600
    
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Shop information
    SHOP_NAME = "মানালী জুয়েলার্স"
    SHOP_AREA = "কুথানগর, নজিরা"
    SHOP_PHONE = "+919876543210"
    SHOP_WHATSAPP = "+919876543210"
    
    # Default rates
    DEFAULT_GST = 3.0
    DEFAULT_GOLD_RATE = 6450
    DEFAULT_SILVER_RATE = 78
