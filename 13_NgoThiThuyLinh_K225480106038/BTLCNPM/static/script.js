function scrollToForm() {
    document.getElementById("bookingSection").scrollIntoView({ behavior: "smooth" });
}

const selectTuyen = document.getElementById("selectTuyen");
const selectLichTrinh = document.getElementById("selectLichTrinh");
const giaVeInput = document.getElementById("giaVe");

// Load danh sách tuyến từ API
async function loadTuyen() {
    const res = await fetch("/api/tuyen");
    const data = await res.json();

    selectTuyen.innerHTML = '<option value="">-- Chọn tuyến --</option>';

    data.forEach(t => {
        selectTuyen.innerHTML += `
            <option value="${t.MaTuyen}">${t.TenTuyen}</option>
        `;
    });
}

// Khi chọn tuyến → load lịch trình
selectTuyen.addEventListener("change", async function () {
    const maTuyen = this.value;
    selectLichTrinh.innerHTML = '<option value="">Đang tải dữ liệu...</option>';
    giaVeInput.value = "";

    if (!maTuyen) {
        selectLichTrinh.innerHTML = '<option value="">-- Chọn tuyến trước --</option>';
        return;
    }

    const res = await fetch(`/api/lichtrinh/${maTuyen}`);
    const data = await res.json();

    selectLichTrinh.innerHTML = '<option value="">-- Chọn chuyến --</option>';

    data.forEach(lt => {
        selectLichTrinh.innerHTML += `
            <option value="${lt.MaLichTrinh}" data-gia="${lt.GiaCoBan}">
                🚆 ${lt.TenTau} | ${lt.NgayDi} (${lt.GioDi} → ${lt.GioDen})
            </option>
        `;
    });
});

// Khi chọn chuyến → hiển thị giá vé
selectLichTrinh.addEventListener("change", function() {
    const price = this.options[this.selectedIndex].dataset.gia;
    giaVeInput.value = price + " VND";
});

// Tự load tuyến khi vào trang
loadTuyen();


// ============================
// CHUYỂN ĐỔI ẨN / HIỆN SECTION
// ============================

function showBooking() {
    document.getElementById("bookingSection").classList.remove("hidden");
    document.getElementById("historySection").classList.add("hidden");
    document.getElementById("bookingSection").scrollIntoView({ behavior: "smooth" });
}

function showHistory() {
    document.getElementById("historySection").classList.remove("hidden");
    document.getElementById("bookingSection").classList.add("hidden");
    document.getElementById("historySection").scrollIntoView({ behavior: "smooth" });
}


// ============================
// THANH TOÁN & HỦY VÉ
// ============================

function thanhToan(id) {
    if (!confirm("Bạn có chắc muốn thanh toán vé này?")) return;

    fetch(`/payment/${id}`, {
        method: "POST"
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message);
        location.reload();
    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối tới server!");
    });
}

function huyVe(id) {
    if (!confirm("Bạn có chắc chắn muốn hủy vé này không?")) return;

    fetch(`/cancel/${id}`, {
        method: "POST"
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message);
        location.reload();
    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối tới server!");
    });
}
