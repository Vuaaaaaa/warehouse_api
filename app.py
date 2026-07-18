from flask import Flask, jsonify, request
import pyodbc

app = Flask(__name__)

# Thêm dòng cấu hình này để hiển thị tiếng Việt chuẩn trên trình duyệt
app.json.ensure_ascii = False

# 1. Cấu hình chuỗi kết nối tới SQL Server của bạn
# CHÚ Ý: Hãy thay đổi ServerName cho đúng với tên Server hiển thị trên SSMS của bạn.
# Thường là: 'LOCALHOST' hoặc '.' hoặc tên máy tính của bạn (ví dụ: 'LAPTOP-XXXXX\SQLEXPRESS')
conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-AHU5FGU\\SQLEXPRESS;"
    "Database=WarehouseDB;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"  # Dòng này cực kỳ quan trọng để sửa lỗi SSL giống trên SSMS lúc nãy
)


# Hàm bổ trợ để kết nối database
def get_db_connection():
    return pyodbc.connect(conn_str)


# 2. Định nghĩa API đầu tiên: Lấy danh sách sản phẩm (GET /products)
@app.route('/products', methods=['GET'])
def get_products():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Viết câu lệnh SQL truy vấn kết hợp (JOIN) để lấy cả tên Nhà cung cấp
        query = """
            SELECT p.ProductID, p.ProductName, p.Price, p.Quantity, s.SupplierName 
            FROM Products p
            INNER JOIN Suppliers s ON p.SupplierID = s.SupplierID
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        # Chuyển đổi dữ liệu từ database thành danh sách dạng JSON
        products = []
        for row in rows:
            products.append({
                "id": row.ProductID,
                "name": row.ProductName,
                "price": float(row.Price),  # Chuyển Decimal sang float để JSON hiểu được
                "quantity": row.Quantity,
                "supplier_name": row.SupplierName
            })

        cursor.close()
        conn.close()

        # Trả về kết quả dạng JSON cho client
        return jsonify(products), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 3. Định nghĩa API thứ hai: Thêm sản phẩm mới (POST /products)
@app.route('/products', methods=['POST'])
def add_product():
    try:
        # Lấy dữ liệu dạng JSON do người dùng gửi lên
        data = request.get_json()

        # Đọc các thông tin từ dữ liệu gửi lên
        name = data.get('name')
        price = data.get('price')
        quantity = data.get('quantity')
        supplier_id = data.get('supplier_id')

        # Kiểm tra xem người dùng có nhập thiếu thông tin bắt buộc không
        if not name or not price or not supplier_id:
            return jsonify({"error": "Thiếu thông tin bắt buộc (name, price, supplier_id)"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Viết câu lệnh INSERT của bạn vào đây
        query = """
            INSERT INTO Products (ProductName, Price, Quantity, SupplierID)
            VALUES (?, ?, ?, ?)
        """
        # Truyền các tham số an toàn vào dấu ? để tránh lỗi bảo mật SQL Injection
        cursor.execute(query, (name, price, quantity, supplier_id))

        conn.commit()  # CỰC KỲ QUAN TRỌNG: Phải commit thì SQL Server mới lưu dữ liệu xuống ổ đĩa

        cursor.close()
        conn.close()

        return jsonify({"message": "Thêm sản phẩm thành công!"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 4. Định nghĩa API Sửa thông tin sản phẩm (PUT /products/<id>)
@app.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    try:
        data = request.get_json()
        new_price = data.get('price')
        new_quantity = data.get('quantity')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Cập nhật giá và số lượng dựa theo product_id
        query = """
            UPDATE Products 
            SET Price = ?, Quantity = ? 
            WHERE ProductID = ?
        """
        cursor.execute(query, (new_price, new_quantity, product_id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": f"Đã cập nhật sản phẩm có ID = {product_id} thành công!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 5. Định nghĩa API Xóa sản phẩm (DELETE /products/<id>)
@app.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "DELETE FROM Products WHERE ProductID = ?"
        cursor.execute(query, (product_id,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": f"Đã xóa sản phẩm có ID = {product_id} thành công!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#6. Định nghĩa API Lấy thông tin số lượng sản phẩm của nhà cung cấp
@app.route('/suppliers/summary', methods=['GET'])
def get_products_by_supplier():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = ("SELECT s.SupplierName, SUM(p.Quantity) AS Quantity "
                 "FROM Products p "
                 "INNER JOIN Suppliers s ON p.SupplierID = s.SupplierID "
                 "GROUP BY s.SupplierName")

        cursor.execute(query)
        rows = cursor.fetchall()

        products = []
        for row in rows:
            products.append({
                "supplier_name": row.SupplierName,
                "total_quantity": row.Quantity
            })

        cursor.close()
        conn.close()

        return jsonify(products), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 3. Chạy ứng dụng Flask
if __name__ == '__main__':
    app.run(debug=True, port=5000)