@app.route("/api/mon-by-ban")
def api_mon_by_ban():
    try:
        ban_id = request.args.get("ban_id")
        if not ban_id: return jsonify([])
        
        # Tìm kiếm hóa đơn chưa thanh toán bằng cách quét cả chuỗi và ObjectId nếu có thể
        query_ban_ids = [str(ban_id)]
        if oid(ban_id):
            query_ban_ids.append(oid(ban_id))
            
        hd = col_hd.find_one({
            "ban_id": {"$in": query_ban_ids}, 
            "trang_thai": "chua_thanhtoan"
        })
        
        if not hd: return jsonify([])
        
        cts = list(col_ct.find({"hoa_don_id": str(hd["_id"])}))
        data = []
        for ct in cts:
            mon = col_mon.find_one({"_id": oid(ct["san_pham_id"])}) if oid(ct["san_pham_id"]) else None
            data.append({
                "id": str(ct["_id"]), 
                "ten_mon": mon["ten_mon"] if mon else "Món không tồn tại", 
                "so_luong": ct["so_luong"], 
                "gia": ct["don_gia"]
            })
        return jsonify(data)
    except Exception as e:
        print(f"Lỗi api_mon_by_ban: {e}")
        return jsonify([]), 500

@app.route("/api/goi-mon", methods=["POST"])
def api_goi_mon():
    try:
        d = request.get_json()
        ban_id = str(d.get("ban_id"))
        mon_id = d.get("mon_id")
        sl = int(d.get("so_luong", 1))
        
        mon = col_mon.find_one({"_id": oid(mon_id)})
        if not mon: return jsonify({"success": False, "message": "Không tìm thấy món"}), 404
        
        query_ban_ids = [ban_id]
        if oid(ban_id): query_ban_ids.append(oid(ban_id))
        
        hd = col_hd.find_one({"ban_id": {"$in": query_ban_ids}, "trang_thai": "chua_thanhtoan"})
        if not hd:
            hid = col_hd.insert_one({
                "ban_id": ban_id, 
                "trang_thai": "chua_thanhtoan", 
                "ngay_tao": datetime.now(), 
                "ngay_tao_str": datetime.now().strftime("%Y-%m-%d")
            }).inserted_id
            hd = {"_id": hid}
            if oid(ban_id): 
                col_ban.update_one({"_id": oid(ban_id)}, {"$set": {"trang_thai": "co_khach"}})
                
        ex = col_ct.find_one({"hoa_don_id": str(hd["_id"]), "san_pham_id": mon_id})
        if ex: 
            col_ct.update_one({"_id": ex["_id"]}, {"$inc": {"so_luong": sl}})
        else: 
            col_ct.insert_one({
                "hoa_don_id": str(hd["_id"]), 
                "san_pham_id": mon_id, 
                "so_luong": sl, 
                "don_gia": mon["gia"]
            })
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
