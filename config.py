import os

class Config:
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'jewellery-shop-secret-key-2024'

    # Database (move real credentials to environment in production)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'mysql+pymysql://jewellery_user:jewellery_pass123@localhost/jewellery_shop'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_TIMEOUT = 30
    SQLALCHEMY_POOL_RECYCLE = 3600

    # Uploads
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # Defaults used in the app
    DEFAULT_GOLD_RATE = 6450.0
    DEFAULT_SILVER_RATE = 78.0
    DEFAULT_GST = 3.0

    # Shop info (ensure all are present)
    SHOP_NAME = "মানালী জুয়েলার্স"
    SHOP_AREA = "কুথানগর, নজিরা"
    SHOP_PHONE = "+919876543210"
    SHOP_WHATSAPP = "919876543210"

    # Session / cookies (development-friendly defaults)
    # In production set SESSION_COOKIE_SECURE = True and use HTTPS
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'