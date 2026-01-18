from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pymysql

db = SQLAlchemy()

class GoldRate(db.Model):
    __tablename__ = 'gold_rates'
    
    id = db.Column(db.Integer, primary_key=True)
    gold_22k = db.Column(db.Float, nullable=False)
    silver = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'gold_22k': self.gold_22k,
            'silver': self.silver,
            'updated_at': self.updated_at.strftime('%I:%M %p')
        }

class GST(db.Model):
    __tablename__ = 'gst'
    
    id = db.Column(db.Integer, primary_key=True)
    percentage = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'percentage': self.percentage,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_bn = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_bn': self.name_bn,
            'image': self.image if self.image else None,
            'created_at': self.created_at.strftime('%Y-%m-%d')
        }

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    name_bn = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    description_bn = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    purity = db.Column(db.String(10), nullable=False)  # 22K, 18K, etc.
    weight = db.Column(db.Float, nullable=False)
    making_charge = db.Column(db.Float, nullable=False)
    stock_status = db.Column(db.String(20), default='In Stock')
    images = db.Column(db.Text)  # Comma separated image paths
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    category = db.relationship('Category', backref=db.backref('products', lazy=True))
    
    def to_dict(self):
        images_list = []
        if self.images:
            images_list = [img.strip() for img in self.images.split(',') if img.strip()]
        
        return {
            'id': self.id,
            'name': self.name,
            'name_bn': self.name_bn,
            'description': self.description_bn,
            'category_id': self.category_id,
            'purity': self.purity,
            'weight': self.weight,
            'making_charge': self.making_charge,
            'stock_status': self.stock_status,
            'images': images_list,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None
        }
