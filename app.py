from flask import Flask, jsonify, request
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from flasgger import Swagger
import pyodbc

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "super-secret-key-quan-ly-kho-123!"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)
jwt = JWTManager(app)
swagger = Swagger(app)

# Thống nhất hiển thị tiếng Việt chuẩn trên trình duyệt
app.json.ensure_ascii = False

conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-AHU5FGU\\SQLEXPRESS;"
    "Database=WarehouseDB;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)


def get_db_connection():
    return pyodbc.connect(conn_str)

@app.route('/register', methods=['POST'])
def register():
    """
    API Register Account
    ---
    tags:
        - Authentication
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                username:
                    type: string
                    example: nv_kho1
                password:
                    type: string
                    example: 123456
                full_name:
                    type: string
                    example: Nguyễn Văn A
    responses:
      201:
        description: Đăng ký thành công
      400:
        description: Dữ liệu không hợp lệ hoặc Username đã tồn tại
    """
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        full_name = data.get("full_name")

        if not username or not password or not full_name:
            return jsonify({"success": False, "error": "Thiếu thông tin bắt buộc"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT UserID FROM Users WHERE username = ?"
        cursor.execute(query, (username,))
        row = cursor.fetchone()
        if row:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "error": "Username đã tồn tại"}), 400
        hash_password = generate_password_hash(password)
        insert_query = ("INSERT INTO Users (Username, PasswordHash, FullName) "
                        "VALUES (?, ?, ?)")
        cursor.execute(insert_query, (username, hash_password, full_name))
        conn.commit()

        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Đăng ký tài khoản thành công!"}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
#1. Login
@app.route('/login', methods=['POST'])
def login():
    """
    API Login lấy JWT Token
    ---
    tags:
        - Authentication
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                username:
                    type: string
                    example: admin
                password:
                    type: string
                    example: 123456
    responses:
        201:
            description: Đăng nhập thành công, trả về access_token
        400:
            description: Thiếu thông tin đăng nhập
        401:
            description: Sai tài khoản hoặc mật khẩu
    """
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"success": False, "error": "Vui lòng nhập đầy đủ thông tin tài khoản"}), 400
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT Username, PasswordHash, Role FROM Users WHERE username = ?"
        cursor.execute(query, (username,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return jsonify({"success": False, "error": "Tài khoản hoặc mật khẩu không đúng"}), 401

        if(check_password_hash(row.PasswordHash, password)):
            user_identity = {"username": row.Username, "role": row.Role}
            access_token = create_access_token(
                identity=str(row.UserID),
                additional_claims={"username": row.Username, "role": row.Role}
            )
            return jsonify({
                "success": True,
                "message": "Đăng nhập thành công",
                "access_token": access_token
            }), 201
        else:
            return jsonify({"success": False, "error": "Tài khoản hoặc mật khẩu không đúng"}), 401
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 2. API: Lấy danh sách sản phẩm (GET /products)
@app.route('/products', methods=['GET'])
@jwt_required()
def get_products():
    """
    API Lấy danh sách toàn bộ sản phẩm trong kho
    ---
    tags:
      - Products
    responses:
      200:
        description: Danh sách sản phẩm kèm thông tin nhà cung cấp
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
              price:
                type: number
              quantity:
                type: integer
              supplier_name:
                type: string
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT p.ProductID, p.ProductName, p.Price, p.Quantity, s.SupplierName 
            FROM Products p
            INNER JOIN Suppliers s ON p.SupplierID = s.SupplierID
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        products = []
        for row in rows:
            products.append({
                "id": row.ProductID,
                "name": row.ProductName,
                "price": float(row.Price),
                "quantity": row.Quantity,
                "supplier_name": row.SupplierName
            })

        cursor.close()
        conn.close()

        return jsonify(products), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 3. API: Thêm sản phẩm mới (POST /products)
@app.route('/products', methods=['POST'])
@jwt_required()
def add_product():
    """
    API Thêm sản phẩm vào kho
    ---
    tags:
      - Products
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Bàn chải đánh răng"
            price:
              type: number
              example: 15000
            quantity:
              type: integer
              example: 25
            supplier_id:
              type: integer
              example: 1
    responses:
      201:
        description: Sản phẩm được thêm thành công
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Thêm sản phẩm thành công!"
      400:
        description: Dữ liệu không hợp lệ hoặc sản phẩm đã tồn tại
      500:
        description: Đã xảy ra lỗi hệ thống
    """
    try:
        data = request.get_json()
        name = data.get('name')
        price = data.get('price')
        quantity = data.get('quantity')
        supplier_id = data.get('supplier_id')

        if not name or price is None or supplier_id is None:
            return jsonify({"success": False, "error": "Thiếu thông tin bắt buộc (name, price, supplier_id)"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Kiểm tra trùng tên sản phẩm theo nhà cung cấp
        check_query = "SELECT COUNT(*) FROM Products WHERE ProductName = ? AND SupplierID = ?"
        cursor.execute(check_query, (name, supplier_id))
        result = cursor.fetchone()
        if result[0] > 0:
            cursor.close()
            conn.close()
            return jsonify(
                {"success": False, "error": f"Sản phẩm '{name}' của nhà cung cấp này đã tồn tại trên hệ thống"}), 400

        query = """
            INSERT INTO Products (ProductName, Price, Quantity, SupplierID)
            VALUES (?, ?, ?, ?)
        """
        cursor.execute(query, (name, price, quantity, supplier_id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"success": True, "message": "Thêm sản phẩm thành công!"}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 4. API: Sửa thông tin sản phẩm (PUT /products/<id>)
@app.route('/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    """
    API Sửa sản phẩm trong kho
    ---
    tags:
      - Products
    parameters:
      - name: product_id
        in: path
        required: true
        type: integer
        description: ID của sản phẩm cần sửa
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            price:
              type: number
              example: 20000
            quantity:
              type: integer
              example: 50
    responses:
      200:
        description: Sản phẩm được sửa thành công
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Đã cập nhật sản phẩm thành công!"
      500:
        description: Đã xảy ra lỗi hệ thống
    """
    try:
        data = request.get_json()
        new_price = data.get('price')
        new_quantity = data.get('quantity')

        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            UPDATE Products 
            SET Price = ?, Quantity = ? 
            WHERE ProductID = ?
        """
        cursor.execute(query, (new_price, new_quantity, product_id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"success": True, "message": f"Đã cập nhật sản phẩm có ID = {product_id} thành công!"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 5. API: Xóa sản phẩm (DELETE /products/<id>)
@app.route('/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    """
    API Xóa sản phẩm trong kho
    ---
    tags:
      - Products
    parameters:
      - name: product_id
        in: path
        required: true
        type: integer
        description: ID của sản phẩm cần xóa
    responses:
      200:
        description: Sản phẩm được xóa thành công
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Đã xóa sản phẩm thành công!"
      400:
        description: Không tìm thấy sản phẩm
      500:
        description: Đã xảy ra lỗi hệ thống
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        check_query = "SELECT COUNT(*) FROM Products WHERE ProductID = ?"
        cursor.execute(check_query, (product_id,))
        result = cursor.fetchone()
        if result[0] == 0:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": f"Không tìm thấy sản phẩm có ID = {product_id} để xóa!"}), 400

        query = "DELETE FROM Products WHERE ProductID = ?"
        cursor.execute(query, (product_id,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"success": True, "message": f"Đã xóa sản phẩm có ID = {product_id} thành công!"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 6. API: Thống kê số lượng sản phẩm theo nhà cung cấp (GET /suppliers/summary)
@app.route('/suppliers/summary', methods=['GET'])
@jwt_required()
def get_products_by_supplier():
    """
    API Lấy tổng số lượng sản phẩm của các nhà cung cấp
    ---
    tags:
      - Reports
    responses:
      200:
        description: Danh sách tổng số lượng sản phẩm theo từng nhà cung cấp
        schema:
          type: array
          items:
            type: object
            properties:
              supplier_name:
                type: string
              total_quantity:
                type: integer
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT s.SupplierName, SUM(p.Quantity) AS TotalQty 
            FROM Products p 
            INNER JOIN Suppliers s ON p.SupplierID = s.SupplierID 
            GROUP BY s.SupplierName
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        summary_data = []
        for row in rows:
            summary_data.append({
                "supplier_name": row.SupplierName,
                "total_quantity": row.TotalQty if row.TotalQty is not None else 0
            })

        cursor.close()
        conn.close()

        return jsonify(summary_data), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
#6. API Nhập kho
@app.route('/products/<int:product_id>/import', methods=['POST'])
@jwt_required()
def import_stock(product_id):
    """
    API Nhập kho
    ---
    tags:
      - Inventory
    parameters:
        - name: product_id
          in: path
          required: true
          type: integer
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                amount:
                    type: integer
                    example: 50
                    description: Số lượng hàng cần nhập thêm
    responses:
        200:
            description: Nhập kho thành công
        400:
            description: Số lượng nhập không hợp lệ
        404:
            description: Sản phẩm không tồn tại
    """
    try:
        data = request.get_json()
        amount = data.get('amount')

        if not amount or amount < 0:
            return jsonify({"success": False, "error": f"Số lượng cần phải nhập lớn hơn 0"}), 400
        conn = get_db_connection()
        cursor = conn.cursor()

        #Kiểm tra xem hàng còn tồn kho không
        query = "SELECT COUNT(*) FROM Products WHERE ProductID = ?"
        cursor.execute(query, (product_id,))
        result = cursor.fetchone()
        if result[0] == 0:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": f"Không tìm thấy sản phẩm có ID = {product_id}!"}), 404

        query = "UPDATE Products SET Quantity = Quantity + ? WHERE ProductID = ?"
        cursor.execute(query, (amount, product_id))
        conn.commit()

        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Nhập kho thành công!"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

#6. API Xuất kho
@app.route('/products/<int:product_id>/export', methods=['POST'])
@jwt_required()
def export_stock(product_id):
    """
    API Xuất kho
    ---
    tags:
      - Inventory
    parameters:
        - name: product_id
          in: path
          required: true
          type: integer
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                amount:
                    type: integer
                    example: 50
                    description: Số lượng hàng cần xuất ra
    responses:
        200:
            description: Xuất kho thành công
        400:
            description: Số lượng xuất không hợp lệ
        404:
            description: Sản phẩm không tồn tại
    """
    try:
        data = request.get_json()
        amount = data.get('amount')

        if not amount or amount < 0:
            return jsonify({"success": False, "error": f"Số lượng cần phải nhập lớn hơn 0"}), 400
        conn = get_db_connection()
        cursor = conn.cursor()

        #Kiểm tra số lượng hiện tại trong kho không
        query = "SELECT Quantity FROM Products WHERE ProductID = ?"
        cursor.execute(query, (product_id,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": f"Không tìm thấy sản phẩm có ID = {product_id}!"}), 404
        current_qty = row.Quantity
        if current_qty < amount:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "error": f"Không đủ hàng trong kho! Hiện tại chỉ còn {current_qty} sản phẩm."}), 400

        query = "UPDATE Products SET Quantity = Quantity - ? WHERE ProductID = ?"
        cursor.execute(query, (amount, product_id))
        conn.commit()

        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Xuất kho thành công!"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)