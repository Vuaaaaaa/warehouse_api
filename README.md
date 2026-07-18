# Warehouse Inventory Management System API

Dự án xây dựng hệ thống API quản lý kho hàng, quản lý sản phẩm và nhà cung cấp sử dụng Python Flask và SQL Server.

## 🛠 Công nghệ sử dụng
- **Backend:** Python, Flask API
- **Database:** Microsoft SQL Server
- **Thư viện kết nối:** pyodbc

## ⚙️ Hướng dẫn cài đặt & Chạy dự án

1. **Clone dự án về máy:**
   ```bash
   git clone https://github.com/Vuaaaaaa/warehouse_api
   cd warehouse_api
   
2. **Cài đặt môi trường ảo & Thư viện:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  
   # Trên Windows dùng: .venv\Scripts\activate
   # Trên Mac/Linux dùng: .venv/bin/activate
    pip install -r requirements.txt

3. **Chạy ứng dụng:**
    ```bash
   python app.py