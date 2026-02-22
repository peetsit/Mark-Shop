from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
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

# ===== Models (ตาราง Database) =====
class Product(db.Model):
    """Model สำหรับตาราง Product"""
    __tablename__ = 'product'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    discount = db.Column(db.Float, default=0)  # ส่วนลดเป็นเปอร์เซ็นต์ (0-100)
    
    def get_sale_price(self):
        """คำนวณราคาหลังส่วนลด"""
        return self.price * (1 - self.discount / 100)
    
    def to_dict(self):
        """แปลง Product object เป็น dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'image_url': self.image_url,
            'discount': self.discount,
            'sale_price': self.get_sale_price() if self.discount > 0 else None
        }
    
    def __repr__(self):
        return f'<Product {self.name}>'


# ===== Routes =====
@app.route('/')
def index():
    """หน้าแรก - ดึงข้อมูล Product จาก Database"""
    products = Product.query.all()
    return render_template('index.html', products=products)


@app.route('/cart')
def cart():
    """หน้าตะกร้าสินค้า"""
    return render_template('cart.html')


@app.route('/api/products', methods=['GET'])
def get_products():
    """API สำหรับดึงข้อมูล Product ทั้งหมด"""
    products = Product.query.all()
    return jsonify([product.to_dict() for product in products])


@app.route('/api/products', methods=['POST'])
def create_product():
    """API สำหรับสร้าง Product ใหม่"""
    try:
        data = request.get_json()
        
        # สร้าง Product object ใหม่
        new_product = Product(
            name=data.get('name'),
            price=data.get('price'),
            image_url=data.get('image_url')
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
    return render_template('admin.html', products=products, username=session.get('admin_username'))


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
            
            # ตรวจสอบข้อมูล
            if not name or not price or not image_url:
                return render_template('admin-add-product.html', 
                                     error='กรุณากรอกข้อมูลให้ครบ')
            
            # สร้าง Product object ใหม่
            new_product = Product(
                name=name,
                price=float(price),
                image_url=image_url
            )
            
            # บันทึกลง Database
            db.session.add(new_product)
            db.session.commit()
            
            return redirect(url_for('dashboard'))
        
        except ValueError:
            return render_template('admin-add-product.html', 
                                 error='ราคาต้องเป็นตัวเลข')
        except Exception as e:
            db.session.rollback()
            return render_template('admin-add-product.html', 
                                 error=f'เกิดข้อผิดพลาด: {str(e)}')
    
    return render_template('admin-add-product.html')


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
        # ไม่ข้ามเมื่อมีข้อมูลอยู่เดิม เพราะเราต้องการเพิ่มรายการใหม่ที่ยังไม่มี
        # (ฟังก์ชันจะตรวจสอบชื่อก่อนเพิ่ม)
        # ข้อมูลตัวอย่างหลายรายการ (เพิ่มเติมจากเดิม)
        sample_products = [
            Product(
                name="หูฟังไร้สาย Premium",
                price=2490.00,
                image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=250&fit=crop",
                discount=15
            ),
            Product(
                name="นาฬิกาสมาร์ทวอทช์",
                price=4990.00,
                image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=250&fit=crop",
                discount=20
            ),
            Product(
                name="กระเป๋า Camera Bag",
                price=1890.00,
                image_url="https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=250&fit=crop",
                discount=10
            ),
            Product(
                name="แว่นตากันแดด",
                price=3290.00,
                image_url="https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=400&h=250&fit=crop",
                discount=25
            ),
            # สินค้าเพิ่มเติมตามคำขอ
            Product(
                name="กล้อง DSLR",
                price=15900.00,
                image_url="https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=500&h=300&fit=crop&auto=format",
                discount=30
            ),
            Product(
                name="iPad Pro 12.9",
                price=33900.00,
                image_url="https://www.apple.com/newsroom/images/product/ipad/standard/Apple-iPad-10th-gen-hero-221018.jpg.og.jpg?202602120420",
                discount=35
            ),
            Product(
                name="iPhone 16 Pro Max",
                price=45990.00,
                image_url="https://www.apple.com/newsroom/images/2024/09/apple-debuts-iphone-16-pro-and-iphone-16-pro-max/article/Apple-iPhone-16-Pro-finish-lineup-240909_big.jpg.large.jpg",
                discount=40
            ),
            Product(
                name="Samsung S25 Ultra",
                price=42990.00,
                image_url="https://www.dxomark.com/wp-content/uploads/medias/post-181483/Samsung-Galaxy-S25-Ultra_featured-image-packshot-review.jpg",
                discount=28
            )
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
                    if changed:
                        added.append(existing)  # treat as updated item for logging
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
        
        # เพิ่มคอลัมน์ discount ถ้ายังไม่มี (migration)
        try:
            with db.engine.begin() as conn:
                conn.execute(db.text("ALTER TABLE product ADD COLUMN discount FLOAT DEFAULT 0"))
        except Exception:
            pass  # column already exists
        
        # เพิ่มข้อมูลตัวอย่างถ้า Database ว่างเปล่า
        seed_sample_data()


if __name__ == '__main__':
    # สร้าง Database เมื่อรันครั้งแรก
    init_db()
    
    # รัน Flask Development Server
    print("\n🚀 Starting Infinite Shop Server...")
    print("📍 http://localhost:5000")
    print("💡 Press CTRL+C to stop the server\n")
    
    app.run(debug=True, host='localhost', port=5000)
