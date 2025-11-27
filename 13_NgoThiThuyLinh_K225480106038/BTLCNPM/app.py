from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash
import pyodbc

app = Flask(__name__)
app.secret_key = "secret123"

# ================== KẾT NỐI DATABASE ==================
def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=MSI\\LINH;"
        "DATABASE=HeThongDatVeTau;"
        "UID=sa;"
        "PWD=1234;"
        "TrustServerCertificate=yes;"
    )

# ================== HOME ==================
@app.route("/")
def home():
    return render_template("login.html")


# ================== REGISTER ==================
@app.route("/register", methods=["POST"])
def register():
    hoten = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if password != confirm_password:
        return "⚠️ Mật khẩu không khớp!", 400

    conn = get_connection()
    cursor = conn.cursor()

    # Kiểm tra email trùng
    cursor.execute("SELECT 1 FROM KhachHang WHERE Email = ?", email)
    if cursor.fetchone():
        conn.close()
        return "⚠️ Email đã tồn tại!", 400

    # Thêm khách hàng mới
    cursor.execute("""
        INSERT INTO KhachHang (HoTen, Email, MatKhau, NgayTao)
        VALUES (?, ?, ?, GETDATE())
    """, hoten, email, password)

    conn.commit()
    conn.close()

    return "🎉 Đăng ký thành công! Vui lòng quay lại đăng nhập."


# ================== LOGIN ==================
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    conn = get_connection()
    cursor = conn.cursor()

    # Chỉ đăng nhập khách hàng
    cursor.execute("SELECT * FROM KhachHang WHERE HoTen = ?", username)
    row = cursor.fetchone()

    if row and row.MatKhau == password:
        session["role"] = "customer"
        session["user_id"] = row.MaKhachHang  # explicit column name
        session["username"] = row.HoTen
        conn.close()

        return jsonify({
            "success": True,
            "message": "Đăng nhập thành công!"
        })

    conn.close()
    return jsonify({
        "success": False,
        "message": "❌ Sai tên đăng nhập hoặc mật khẩu!"
    })


# ================== API TUYẾN ==================
@app.route("/api/tuyen")
def api_tuyen():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT MaTuyen, DiemDi, DiemDen FROM TuyenDuong")
    data = [{
        "MaTuyen": row.MaTuyen,
        "TenTuyen": f"{row.DiemDi} - {row.DiemDen}"
    } for row in cursor.fetchall()]

    conn.close()
    return jsonify(data)


# ================== API LỊCH TRÌNH ==================
@app.route("/api/lichtrinh/<int:ma_tuyen>")
def api_lichtrinh(ma_tuyen):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT lt.MaLichTrinh, lt.GiaCoBan, lt.NgayDi, lt.GioDi, lt.GioDen, t.TenTau
        FROM LichTrinh lt
        JOIN Tau t ON lt.MaTau = t.MaTau
        WHERE lt.MaTuyen = ?
    """, ma_tuyen)

    data = [{
        "MaLichTrinh": row.MaLichTrinh,
        "GiaCoBan": float(row.GiaCoBan),
        "NgayDi": row.NgayDi.strftime("%d/%m/%Y") if row.NgayDi else None,
        "GioDi": row.GioDi.strftime("%H:%M") if row.GioDi else None,
        "GioDen": row.GioDen.strftime("%H:%M") if row.GioDen else None,
        "TenTau": row.TenTau
    } for row in cursor.fetchall()]

    conn.close()
    return jsonify(data)


# ================== CUSTOMER DASHBOARD ==================
@app.route("/customer")
def customer_index():
    if session.get("role") != "customer":
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor()

    user_id = session.get("user_id")
    cursor.execute("""
        SELECT dv.MaDatVe, dv.NgayTao, ve.SoGhe, ve.GiaVe, dv.TrangThai,
               dv.ThanhToan, dv.DaHuy
        FROM DatVe dv
        LEFT JOIN Ve ve ON dv.MaDatVe = ve.MaDatVe
        WHERE dv.MaKhachHang = ?
        ORDER BY dv.NgayTao DESC
    """, user_id)

    lichsu = cursor.fetchall()
    conn.close()

    return render_template("index.html", lichsu=lichsu)


# ================== ĐẶT VÉ ==================
@app.route("/datve", methods=["POST"])
def dat_ve():
    if session.get("role") != "customer":
        return redirect("/")

    user_id = session.get("user_id")
    ma_lich = request.form.get("ma_lich_trinh")
    gia = request.form.get("gia", "0").replace(" VND", "").replace(",", "").strip()

    try:
        gia_decimal = float(gia)
    except:
        gia_decimal = 0.0

    conn = get_connection()
    cursor = conn.cursor()

    # TẠO ĐẶT VÉ
    cursor.execute("""
        INSERT INTO DatVe (MaKhachHang, MaLichTrinh, TongTien, TrangThai, NgayTao)
        OUTPUT INSERTED.MaDatVe
        VALUES (?, ?, ?, N'Chờ thanh toán', GETDATE())
    """, user_id, ma_lich, gia_decimal)

    result = cursor.fetchone()
    if not result:
        conn.rollback()
        conn.close()
        flash("❌ Lỗi khi tạo đơn đặt vé!", "error")
        return redirect("/customer")

    ma_dat_ve = result[0]

    # TẠO SỐ GHẾ
    cursor.execute("""
        SELECT t.TongSoGhe, lt.SoGheConLai
        FROM LichTrinh lt
        JOIN Tau t ON lt.MaTau = t.MaTau
        WHERE lt.MaLichTrinh = ?
    """, ma_lich)

    row = cursor.fetchone()
    if row:
        so_ghe = f"A{row.TongSoGhe - row.SoGheConLai + 1:02d}"
    else:
        so_ghe = "A01"

    # TẠO VÉ
    cursor.execute("""
        INSERT INTO Ve (MaDatVe, SoGhe, GiaVe, TrangThai)
        VALUES (?, ?, ?, N'Đã đặt')
    """, ma_dat_ve, so_ghe, gia_decimal)

    # TRỪ GHẾ CÒN LẠI
    cursor.execute("""
        UPDATE LichTrinh
        SET SoGheConLai = SoGheConLai - 1
        WHERE MaLichTrinh = ?
    """, ma_lich)

    conn.commit()
    conn.close()

    # THÔNG BÁO THÀNH CÔNG
    flash("🎉 Đặt vé thành công!", "success")
    return redirect("/customer")


# ================== THANH TOÁN VÉ ==================
@app.route("/payment/<int:ma_dat_ve>", methods=["POST"])
def payment(ma_dat_ve):
    if session.get("role") != "customer":
        return jsonify({"success": False, "message": "Bạn chưa đăng nhập!"}), 401

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE DatVe
        SET ThanhToan = N'Đã thanh toán', TrangThai = N'Đã thanh toán'
        WHERE MaDatVe = ? AND MaKhachHang = ?
    """, ma_dat_ve, session["user_id"])

    if cursor.rowcount == 0:
        conn.commit()
        conn.close()
        return jsonify({"success": False, "message": "Không tìm thấy đặt vé này."}), 404

    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Thanh toán thành công!"})


# ================== HỦY VÉ ==================
@app.route("/cancel/<int:ma_dat_ve>", methods=["POST"])
def cancel_ticket(ma_dat_ve):
    if session.get("role") != "customer":
        return jsonify({"success": False, "message": "Bạn chưa đăng nhập!"}), 401

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT MaLichTrinh, DaHuy
        FROM DatVe
        WHERE MaDatVe = ? AND MaKhachHang = ?
    """, ma_dat_ve, session["user_id"])

    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"success": False, "message": "Không tìm thấy đặt vé này."}), 404

    ma_lichtrinh = row.MaLichTrinh
    da_huy = row.DaHuy

    if da_huy:
        conn.close()
        return jsonify({"success": False, "message": "Đặt vé đã bị hủy trước đó."}), 400

    cursor.execute("""
        UPDATE DatVe
        SET DaHuy = 1, TrangThai = N'Đã hủy'
        WHERE MaDatVe = ? AND MaKhachHang = ?
    """, ma_dat_ve, session["user_id"])

    cursor.execute("""
        UPDATE LichTrinh
        SET SoGheConLai = SoGheConLai + 1
        WHERE MaLichTrinh = ?
    """, ma_lichtrinh)

    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Hủy vé thành công!"})


# ================== LOGOUT ==================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ================== RUN ==================
if __name__ == "__main__":
    app.run(debug=True)
