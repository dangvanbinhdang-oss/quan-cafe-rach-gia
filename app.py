@app.route('/api/tach-ban', methods=['POST'])
def tach_ban():
    data = request.json
    ban_nguon_id = data.get('ban_nguon')
    ban_dich_id = data.get('ban_dich')
    chi_tiet_ids = data.get('chi_tiet_ids', []) # Danh sách ID món trong bảng chi tiết hóa đơn cần tách

    if not ban_nguon_id or not ban_dich_id or not chi_tiet_ids:
        return jsonify({'success': False, 'message': 'Thiếu thông tin tách bàn'})

    try:
        # 1. Tìm hóa đơn đang mở của bàn nguồn
        bill_nguon = HoaDon.query.filter_by(ban_id=ban_nguon_id, trang_thai='chua_thanh_toan').first()
        if not bill_nguon:
            return jsonify({'success': False, 'message': 'Bàn nguồn không có hóa đơn hoạt động'})

        # 2. Tìm hoặc tạo mới hóa đơn cho bàn đích
        bill_dich = HoaDon.query.filter_by(ban_id=ban_dich_id, trang_thai='chua_thanh_toan').first()
        if not bill_dich:
            bill_dich = HoaDon(ban_id=ban_dich_id, trang_thai='chua_thanh_toan')
            db.session.add(bill_dich)
            db.session.commit()
            
            # Cập nhật trạng thái bàn đích thành 'co_khach'
            ban_dich = Ban.query.get(ban_dich_id)
            if ban_dich:
                ban_dich.trang_thai = 'co_khach'

        # 3. Chuyển các món được chọn từ bill_nguon sang bill_dich
        for ct_id in chi_tiet_ids:
            chi_tiet = ChiTietHoaDon.query.filter_by(id=ct_id, hoa_don_id=bill_nguon.id).first()
            if chi_tiet:
                chi_tiet.hoa_don_id = bill_dich.id

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
