from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# สร้าง Flask Application
app = Flask(__name__)

# ตั้งค่าครับ
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'shop.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'infinite-shop-secret-key-2026'  # สำหรับ session

# สร้าง Database Instance
db = SQLAlchemy(app)

# Register Jinja2 filters and globals
@app.template_filter('int')
def to_int(value):
    """Convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

app.jinja_env.filters['int'] = to_int

# ===== Models (ตาราง Database) =====
class Category(db.Model):
    """Model สำหรับตาราง Category"""
    __tablename__ = 'category'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(500), default='')
    
    # Relationship
    products = db.relationship('Product', backref='category', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }
    
    def __repr__(self):
        return f'<Category {self.name}>'


class Product(db.Model):
    """Model สำหรับตาราง Product"""
    __tablename__ = 'product'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    discount = db.Column(db.Float, default=0)  # ส่วนลดเป็นเปอร์เซ็นต์ (0-100)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    description = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    reviews = db.relationship('Review', backref='product', lazy=True, cascade='all, delete-orphan')
    
    def get_sale_price(self):
        """คำนวณราคาหลังส่วนลด"""
        return self.price * (1 - self.discount / 100)
    
    def get_average_rating(self):
        """คำนวณคะแนนเฉลี่ย"""
        if not self.reviews:
            return 0
        total = sum(review.rating for review in self.reviews)
        return total / len(self.reviews)
    
    def get_review_count(self):
        """นับจำนวนรีวิว"""
        return len(self.reviews)
    
    def to_dict(self):
        """แปลง Product object เป็น dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'image_url': self.image_url,
            'discount': self.discount,
            'sale_price': self.get_sale_price() if self.discount > 0 else None,
            'category': self.category.to_dict() if self.category else None,
            'description': self.description,
            'rating': round(self.get_average_rating(), 1),
            'review_count': self.get_review_count()
        }
    
    def __repr__(self):
        return f'<Product {self.name}>'


class Review(db.Model):
    """Model สำหรับตาราง Review"""
    __tablename__ = 'review'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'customer_name': self.customer_name,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M')
        }
    
    def __repr__(self):
        return f'<Review {self.product_id} - {self.rating}★>'


class Order(db.Model):
    """Model สำหรับตาราง Order"""
    __tablename__ = 'order'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_address = db.Column(db.String(500), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # credit_card, debit_card, promptpay, mobile_banking, bank_transfer, cod
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, confirmed, shipped, delivered, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def get_payment_method_display(self):
        """ส่งกลับชื่อแสดงของวิธีการชำระเงิน"""
        payment_methods = {
            'credit_card': 'บัตรเครดิต',
            'debit_card': 'บัตรเดบิต',
            'promptpay': 'PromptPay',
            'mobile_banking': 'Mobile Banking',
            'bank_transfer': 'โอนธนาคาร',
            'cod': 'เก็บเงินปลายทาง'
        }
        return payment_methods.get(self.payment_method, self.payment_method)
    
    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'customer_address': self.customer_address,
            'payment_method': self.payment_method,
            'total_price': self.total_price,
            'status': self.status,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M'),
            'items': [item.to_dict() for item in self.items]
        }
    
    def __repr__(self):
        return f'<Order {self.id}>'


class OrderItem(db.Model):
    """Model สำหรับตาราง OrderItem"""
    __tablename__ = 'order_item'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    # Relationship
    product = db.relationship('Product', backref='order_items')
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else '',
            'quantity': self.quantity,
            'price': self.price
        }
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'


# ===== Routes =====
@app.route('/')
def index():
    """หน้าแรก - ดึงข้อมูล Product จาก Database"""
    products = Product.query.all()
    categories = Category.query.all()
    return render_template('index.html', products=products, categories=categories)


@app.route('/category/<category_name>')
def category_filter(category_name):
    """กรองสินค้าตามหมวดหมู่"""
    category = Category.query.filter_by(name=category_name).first()
    if not category:
        return redirect(url_for('index'))
    
    products = Product.query.filter_by(category_id=category.id).all()
    categories = Category.query.all()
    return render_template('index.html', products=products, categories=categories, selected_category=category_name)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """หน้าละเอียดสินค้า พร้อมรีวิว"""
    product = Product.query.get(product_id)
    if not product:
        return redirect(url_for('index'))
    
    reviews = Review.query.filter_by(product_id=product_id).all()
    return render_template('product-detail.html', product=product, reviews=reviews)


@app.route('/cart')
def cart():
    """หน้าตะกร้าสินค้า"""
    return render_template('cart.html')


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """หน้าชำระเงิน"""
    if request.method == 'POST':
        try:
            # รับข้อมูลจากฟอร์ม
            customer_name = request.form.get('customer_name')
            customer_email = request.form.get('customer_email')
            customer_phone = request.form.get('customer_phone')
            customer_address = request.form.get('customer_address')
            payment_method = request.form.get('payment_method')
            cart_data = request.form.get('cart_data')  # JSON string
            
            import json
            cart_items = json.loads(cart_data) if cart_data else []
            
            if not cart_items:
                return render_template('checkout.html', error='ไม่พบสินค้าในตะกร้า')
            
            # คำนวณยอดรวม
            total_price = sum(item['price'] * item['quantity'] for item in cart_items)
            
            # สร้าง Order ใหม่
            new_order = Order(
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                customer_address=customer_address,
                payment_method=payment_method,
                total_price=total_price,
                status='pending'
            )
            
            # เพิ่ม OrderItems
            for item in cart_items:
                order_item = OrderItem(
                    product_id=item['id'],
                    quantity=item['quantity'],
                    price=item['price']
                )
                new_order.items.append(order_item)
            
            # บันทึกลง Database
            db.session.add(new_order)
            db.session.commit()
            
            return redirect(url_for('checkout_success', order_id=new_order.id))
        
        except Exception as e:
            db.session.rollback()
            return render_template('checkout.html', error=f'เกิดข้อผิดพลาด: {str(e)}')
    
    return render_template('checkout.html')


@app.route('/checkout/success/<int:order_id>')
def checkout_success(order_id):
    """หน้าแสดงกำลังดำเนินการคำสั่งซื้อสำเร็จ"""
    order = Order.query.get(order_id)
    if not order:
        return redirect(url_for('index'))
    
    return render_template('checkout-success.html', order=order)


@app.route('/api/products', methods=['GET'])
def get_products():
    """API สำหรับดึงข้อมูล Product ทั้งหมด"""
    category_id = request.args.get('category_id')
    
    if category_id:
        products = Product.query.filter_by(category_id=category_id).all()
    else:
        products = Product.query.all()
    
    return jsonify([product.to_dict() for product in products])


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """API สำหรับดึงข้อมูล Category ทั้งหมด"""
    categories = Category.query.all()
    return jsonify([category.to_dict() for category in categories])


@app.route('/api/products', methods=['POST'])
def create_product():
    """API สำหรับสร้าง Product ใหม่"""
    try:
        data = request.get_json()
        
        # สร้าง Product object ใหม่
        new_product = Product(
            name=data.get('name'),
            price=data.get('price'),
            image_url=data.get('image_url'),
            category_id=data.get('category_id'),
            description=data.get('description', '')
        )
        
        # เพิ่มลงใน Database
        db.session.add(new_product)
        db.session.commit()
        
        return jsonify({
            'message': 'Product สร้างสำเร็จ',
            'product': new_product.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """API สำหรับดึงข้อมูล Product หนึ่งชิ้น"""
    product = Product.query.get(product_id)
    
    if not product:
        return jsonify({'error': 'Product ไม่พบ'}), 404
    
    return jsonify(product.to_dict())


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """API สำหรับแก้ไข Product"""
    try:
        product = Product.query.get(product_id)
        
        if not product:
            return jsonify({'error': 'Product ไม่พบ'}), 404
        
        data = request.get_json()
        
        # อัปเดตข้อมูล
        if 'name' in data:
            product.name = data['name']
        if 'price' in data:
            product.price = data['price']
        if 'image_url' in data:
            product.image_url = data['image_url']
        if 'category_id' in data:
            product.category_id = data['category_id']
        if 'description' in data:
            product.description = data['description']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Product อัปเดตสำเร็จ',
            'product': product.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """API สำหรับลบ Product"""
    try:
        product = Product.query.get(product_id)
        
        if not product:
            return jsonify({'error': 'Product ไม่พบ'}), 404
        
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({'message': 'Product ลบสำเร็จ'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


# ===== Review Routes =====
@app.route('/api/reviews', methods=['POST'])
def add_review():
    """API เพิ่มรีวิว/ให้คะแนนสินค้า"""
    try:
        data = request.get_json()
        
        product_id = data.get('product_id')
        customer_name = data.get('customer_name')
        rating = int(data.get('rating', 0))
        comment = data.get('comment', '')
        
        # ตรวจสอบข้อมูล
        if rating < 1 or rating > 5:
            return jsonify({'error': 'คะแนนต้องระหว่าง 1-5'}), 400
        
        # ตรวจสอบสินค้า
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': 'สินค้าไม่พบ'}), 404
        
        # สร้าง Review ใหม่
        new_review = Review(
            product_id=product_id,
            customer_name=customer_name,
            rating=rating,
            comment=comment
        )
        
        db.session.add(new_review)
        db.session.commit()
        
        return jsonify({
            'message': 'เพิ่มรีวิวสำเร็จ',
            'review': new_review.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/reviews/<int:product_id>', methods=['GET'])
def get_reviews(product_id):
    """API ดึงรีวิวของสินค้า"""
    reviews = Review.query.filter_by(product_id=product_id).all()
    return jsonify([review.to_dict() for review in reviews])


# ===== Admin Routes =====
def is_admin_logged_in():
    """ตรวจสอบว่า Admin ล้อกอินแล้วหรือไม่"""
    return session.get('admin_logged_in', False)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """หน้า Login สำหรับ Admin"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # ตรวจสอบข้อมูล
        if username == 'admin' and password == '1234':
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='ชื่อผู้ใช้ หรือ รหัสผ่านไม่ถูกต้อง')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """ออกจากระบบ Admin"""
    session.clear()
    return redirect(url_for('login'))


@app.route('/sale')
def sale():
    """หน้าสินค้าลดราคา"""
    products = Product.query.filter(Product.discount > 0).all()
    return render_template('sale.html', products=products)


@app.route('/admin/dashboard')
def dashboard():
    """แดชบอร์ด Admin - แสดงรายการสินค้าทั้งหมด"""
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    products = Product.query.all()
    categories = Category.query.all()
    orders = Order.query.all()
    return render_template('admin.html', products=products, categories=categories, orders=orders, username=session.get('admin_username'))


# ===== Category Management =====
@app.route('/admin/categories', methods=['GET'])
def manage_categories():
    """จัดการหมวดหมู่"""
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    categories = Category.query.all()
    return render_template('admin-categories.html', categories=categories)


@app.route('/admin/categories/add', methods=['POST'])
def add_category():
    """เพิ่มหมวดหมู่ใหม่"""
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    try:
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            return render_template('admin-categories.html', error='กรุณากรอกชื่อหมวดหมู่')
        
        # ตรวจสอบว่ามีอยู่แล้วหรือไม่
        existing = Category.query.filter_by(name=name).first()
        if existing:
            categories = Category.query.all()
            return render_template('admin-categories.html', 
                                 categories=categories,
                                 error='หมวดหมู่นี้มีอยู่แล้ว')
        
        new_category = Category(name=name, description=description)
        db.session.add(new_category)
        db.session.commit()
        
        return redirect(url_for('manage_categories'))
    
    except Exception as e:
        db.session.rollback()
        categories = Category.query.all()
        return render_template('admin-categories.html', 
                             categories=categories,
                             error=f'เกิดข้อผิดพลาด: {str(e)}')


@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    """ลบหมวดหมู่"""
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    try:
        category = Category.query.get(category_id)
        
        if not category:
            return redirect(url_for('manage_categories'))
        
        db.session.delete(category)
        db.session.commit()
    
    except Exception as e:
        db.session.rollback()
    
    return redirect(url_for('manage_categories'))


# ===== Product Management =====
@app.route('/admin/add-product', methods=['GET', 'POST'])
def add_product_admin():
    """เพิ่มสินค้าใหม่จาก Admin"""
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            price = request.form.get('price')
            image_url = request.form.get('image_url')
            category_id = request.form.get('category_id')
            description = request.form.get('description', '')
            
            # ตรวจสอบข้อมูล
            if not name or not price or not image_url:
                categories = Category.query.all()
                return render_template('admin-add-product.html', 
                                     categories=categories,
                                     error='กรุณากรอกข้อมูลให้ครบ')
            
            # สร้าง Product object ใหม่
            new_product = Product(
                name=name,
                price=float(price),
                image_url=image_url,
                category_id=category_id if category_id else None,
                description=description
            )
            
            # บันทึกลง Database
            db.session.add(new_product)
            db.session.commit()
            
            return redirect(url_for('dashboard'))
        
        except ValueError:
            categories = Category.query.all()
            return render_template('admin-add-product.html', 
                                 categories=categories,
                                 error='ราคาต้องเป็นตัวเลข')
        except Exception as e:
            db.session.rollback()
            categories = Category.query.all()
            return render_template('admin-add-product.html', 
                                 categories=categories,
                                 error=f'เกิดข้อผิดพลาด: {str(e)}')
    
    categories = Category.query.all()
    return render_template('admin-add-product.html', categories=categories)


@app.route('/admin/delete-product/<int:product_id>', methods=['POST'])
def delete_product_admin(product_id):
    """ลบสินค้า จาก Admin"""
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    try:
        product = Product.query.get(product_id)
        
        if not product:
            return redirect(url_for('dashboard'))
        
        db.session.delete(product)
        db.session.commit()
    
    except Exception as e:
        db.session.rollback()
    
    return redirect(url_for('dashboard'))


# ===== Seed Sample Data =====
def seed_sample_data():
    """เพิ่มข้อมูลตัวอย่างลงใน Database ถ้าเป็นครั้งแรก"""
    with app.app_context():
        # สร้างหมวดหมู่ถ้ายังไม่มี
        categories_data = [
            {'name': 'Electronics', 'description': 'อิเล็กทรอนิกส์'},
            {'name': 'Computers', 'description': 'คอมพิวเตอร์'},
            {'name': 'Cameras', 'description': 'กล้อง'},
        ]
        
        for cat_data in categories_data:
            existing = Category.query.filter_by(name=cat_data['name']).first()
            if not existing:
                new_category = Category(name=cat_data['name'], description=cat_data['description'])
                db.session.add(new_category)
                print(f"✅ Added category: {cat_data['name']}")
        
        db.session.commit()
        
        # ดึง categories เพื่อใช้ในการสร้าง products
        electronics_cat = Category.query.filter_by(name='Electronics').first()
        computers_cat = Category.query.filter_by(name='Computers').first()
        cameras_cat = Category.query.filter_by(name='Cameras').first()
        
        # ข้อมูลตัวอย่าง Products
        sample_products = [
            # Electronics
            Product(
                name="หูฟังไร้สาย Premium",
                price=2490.00,
                image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=250&fit=crop",
                discount=15,
                category_id=electronics_cat.id if electronics_cat else None,
                description="หูฟังไร้สายคุณภาพสูง มีการบริษัฒน์เสียงที่ชัดเจน"
            ),
            Product(
                name="นาฬิกาสมาร์ทวอทช์",
                price=4990.00,
                image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=250&fit=crop",
                discount=20,
                category_id=electronics_cat.id if electronics_cat else None,
                description="นาฬิกาสมาร์ทวอทช์ พร้อมใจการติดตามสุขภาพ"
            ),
            Product(
                name="แว่นตากันแดด",
                price=3290.00,
                image_url="https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=400&h=250&fit=crop",
                discount=25,
                category_id=electronics_cat.id if electronics_cat else None,
                description="แว่นตากันแดด UV protection 100%"
            ),
            # Computers
            Product(
                name="iPad Pro 12.9",
                price=33900.00,
                image_url="https://www.apple.com/newsroom/images/product/ipad/standard/Apple-iPad-10th-gen-hero-221018.jpg.og.jpg?202602120420",
                discount=35,
                category_id=computers_cat.id if computers_cat else None,
                description="iPad Pro 12.9 นิ้ว หน้าจอ Retina ความเร็ว M2"
            ),
            Product(
                name="iPhone 16 Pro Max",
                price=45990.00,
                image_url="https://www.apple.com/newsroom/images/2024/09/apple-debuts-iphone-16-pro-and-iphone-16-pro-max/article/Apple-iPhone-16-Pro-finish-lineup-240909_big.jpg.large.jpg",
                discount=40,
                category_id=computers_cat.id if computers_cat else None,
                description="iPhone 16 Pro Max กล้อง 48MP กระบวนการ A18 Pro"
            ),
            Product(
                name="Samsung S25 Ultra",
                price=42990.00,
                image_url="https://www.dxomark.com/wp-content/uploads/medias/post-181483/Samsung-Galaxy-S25-Ultra_featured-image-packshot-review.jpg",
                discount=28,
                category_id=computers_cat.id if computers_cat else None,
                description="Samsung Galaxy S25 Ultra โทรศัพท์แฟลกชิป Snapdragon"
            ),
            # Cameras
            Product(
                name="กล้อง DSLR Canon EOS R5",
                price=159900.00,
                image_url="https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=500&h=300&fit=crop&auto=format",
                discount=30,
                category_id=cameras_cat.id if cameras_cat else None,
                description="กล้อง DSLR Canon EOS R5 45MP ระบบ 8K"
            ),
            Product(
                name="กระเป๋า Camera Bag",
                price=1890.00,
                image_url="https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=250&fit=crop",
                discount=10,
                category_id=cameras_cat.id if cameras_cat else None,
                description="กระเป๋ากล้องคุณภาพสูง พร้อมฟองน้ำบุ้ม"
            ),
        ]
        
        try:
            # เพิ่มสินค้าใหม่ตามชื่อถ้ายังไม่มีในฐาน
            added = []
            for item in sample_products:
                existing = Product.query.filter_by(name=item.name).first()
                if not existing:
                    db.session.add(item)
                    added.append(item)
                else:
                    # update URL/price if changed
                    changed = False
                    if existing.image_url != item.image_url:
                        existing.image_url = item.image_url
                        changed = True
                    if existing.price != item.price:
                        existing.price = item.price
                        changed = True
                    if existing.category_id != item.category_id:
                        existing.category_id = item.category_id
                        changed = True
                    if changed:
                        added.append(existing)
            if added:
                db.session.commit()
                print(f"✅ Sample products inserted/updated {len(added)} item(s):")
                for product in added:
                    print(f"   - {product.name} (฿{product.price:.2f})")
            else:
                print("✅ All sample products already exist and are up‑to‑date.")
        
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error inserting sample data: {str(e)}")


# ===== Initialize Database =====
def init_db():
    """สร้าง Database และตาราง ถ้ายังไม่มี"""
    with app.app_context():
        # สร้างตาราง
        db.create_all()
        print("✅ Database initialized successfully!")
        print(f"📁 Database file created: {os.path.abspath('shop.db')}")
        
        # เพิ่มข้อมูลตัวอย่าง
        seed_sample_data()


if __name__ == '__main__':
    # สร้าง Database เมื่อรันครั้งแรก
    init_db()
    
    # รัน Flask Development Server
    print("\n🚀 Starting Infinite Shop Server...")
    print("📍 http://localhost:5000")
    print("💡 Press CTRL+C to stop the server\n")
    
    app.run(debug=True, host='localhost', port=5000)
