from flask import Flask, jsonify
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

# Đọc file HTML bạn vừa lưu (đảm bảo file mã nguồn bạn gửi ở trên được lưu tên là 'index.html' cùng thư mục)
def read_html_file():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None

def parse_hust_sis_program(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Tìm bảng chính chứa chương trình đào tạo của DevExpress
    main_table = soup.find('table', id=re.compile(r'.*gvStudentProgram_DXMainTable'))
    
    if not main_table:
        return []

    parsed_courses = []
    current_ma_loai_hp = ""
    current_loai_hp = ""

    # Duyệt qua từng dòng của bảng
    rows = main_table.find_all('tr')
    for row in rows:
        row_class = row.get('class', [])
        row_id = row.get('id', '')

        # 1. Bóc tách dòng Tiêu đề Nhóm (Mã loại HP / Loại HP)
        if 'dxgvGroupRow' in row_class:
            text_content = row.text.strip()
            if "Mã loại HP:" in text_content:
                current_ma_loai_hp = text_content.split('(')[0].replace('Mã loại HP:', '').strip()
            elif "Loại HP:" in text_content:
                current_loai_hp = text_content.split('(')[0].replace('Loại HP:', '').strip()
            continue

        # 2. Bóc tách dòng Dữ liệu Môn học thực tế
        if 'dxgvDataRow' in row_class:
            cols = row.find_all('td')
            
            # Cấu trúc cột của SIS HUST sau khi phân rã hệ thống cột ẩn của nhóm:
            # Cột 0, 1: Ô trống thụt lề (Indent cells)
            # Cột 2: Mã học phần (Mã HP)
            # Cột 3: Tên học phần (Tên HP)
            # Cột 4: Kỳ học
            # Cột 5: Bắt buộc (Checkbox)
            # Cột 6: Tín chỉ ĐT (TC ĐT)
            # Cột 7: Tín chỉ học (TC học)
            # Cột 8: Mã HP học
            # Cột 9: Ghi chú loại HP
            # Cột 10: Điểm chữ
            # Cột 11: Điểm số
            # Cột 12: Viện / Khoa

            if len(cols) >= 13: # Đảm bảo dòng chứa đầy đủ các cột dữ liệu
                try:
                    ma_hp = cols[2].text.strip()
                    ten_hp = cols[3].text.strip()
                    ky_hoc = cols[4].text.strip()
                    
                    # Kiểm tra checkbox bắt buộc
                    is_required = "Không"
                    chk_box = cols[5].find('span', class_='dxWeb_edtCheckBoxChecked')
                    if chk_box:
                        is_required = "Có"

                    tc_dt = cols[6].text.strip()
                    tc_hoc = cols[7].text.strip()
                    ma_hp_hoc = cols[8].text.strip()
                    ghi_chu = cols[9].text.strip()
                    diem_chu = cols[10].text.strip() if cols[10].text.strip() != " " else ""
                    diem_so = cols[11].text.strip() if cols[11].text.strip() != " " else ""
                    vien_khoa = cols[12].text.strip()

                    # Lọc bỏ các dòng thừa hoặc dòng tiêu đề lọt lưới
                    if ma_hp and ma_hp != "Mã HP":
                        course_obj = {
                            "nhom_ma_loai_hp": current_ma_loai_hp,
                            "nhom_loai_hp": current_loai_hp,
                            "ma_hp": ma_hp,
                            "ten_hp": ten_hp,
                            "ky_hoc": ky_hoc,
                            "bat_buoc": is_required,
                            "tc_dat_doc_tai": tc_dt,
                            "tc_hoc": tc_hoc,
                            "ma_hp_hoc": ma_hp_hoc,
                            "ghi_chu_loai_hp": ghi_chu,
                            "diem_chu": diem_chu,
                            "diem_so": diem_so,
                            "vien_khoa": vien_khoa
                        }
                        parsed_courses.append(course_obj)
                except Exception as e:
                    continue # Bỏ qua nếu dòng lỗi cấu trúc

    return parsed_courses

@app.route('/')
def index():
    return """
    <div style="font-family: Arial, sans-serif; margin: 50px;">
        <h2>HUST SIS HTML Data Parser (DevExpress Configured)</h2>
        <p>Đã tìm thấy tệp cấu trúc chuẩn từ hệ thống SIS của HUST.</p>
        <a href="/get-json-data"><button style="padding: 10px 20px; background-color: #9C1010; color: white; border: none; border-radius: 4px; cursor: pointer;">Trích xuất dữ liệu JSON</button></a>
    </div>
    """

@app.route('/get-json-data')
def get_json_data():
    html_content = read_html_file()
    if not html_content:
        return jsonify({
            "status": "error",
            "message": "Không tìm thấy file 'index.html'. Vui lòng lưu đoạn mã HTML bạn vừa copy thành file 'index.html' và đặt cùng thư mục với file app.py này."
        }), 404

    result_data = parse_hust_sis_program(html_content)
    
    return jsonify({
        "status": "success",
        "total_courses_found": len(result_data),
        "student_name": "Võ Khánh Toàn",
        "student_id": "202516919",
        "data": result_data
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
