import os
from flask import Flask, render_template, request, redirect, jsonify
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import certifi

app = Flask(__name__)
app.secret_key = "cafe_rach_gia_2026"

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://dangvanbinhdang_db_user:mWpNbVmziJcrvnd3@cluster0.q1apjoi.mongodb.net/?appName=Cluster0")

try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), tls=True, serverSelectionTimeoutMS=15000, retryWrites=True)
    client.admin.command('ping')
    print("✅ KET NOI ATLAS THANH CONG!")
except Exception as e:
    print(f"❌ LOI ATLAS: {e}")
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), tls=True, tlsAllowInvalidCertificates=True)

db = client['quan_cafe']
col_ban = db['ban_an']
col_dm = db['danh_muc']
col_mon = db['san_pham']
col_cd = db['cai_dat']
col_hd = db['hoa_don']
col_ct = db['chi_tiet_hoa_don']

def get_cd():
    cd = col_cd.find_one({"_id": "cau_hinh_1"})
    if not cd:
        cd = {"_id": "cau_hinh_1", "ten_quan": "QUÁN CAFE RẠCH GIÁ", "dia_chi": "TP. Rạch Giá, Kiên Giang", "dien_thoai": "0909 123 456"}
        col_cd.insert_one(cd)
    return cd

def oid(s):
    try: return ObjectId(s)
    except: return None

@app.route("/")
def index():
    cd = get_cd()
    bans = list(col_ban.find().sort("_id", 1))
    if not bans:
        col_ban.insert_many([{"ten_ban": f"Bàn {i:02d}", "trang_thai": "trong"} for i in range(1,13)])
        col_dm.insert_many([{"ten_danh_muc": "Cà phê"}, {"ten_danh_muc": "Trà sữa"}, {"ten_danh_muc": "Đồ Ăn Vặt"}])
        bans = list(col_ban.find().sort("_id", 1))
    
    for b in bans:
        b["_id_str"] = str(b["_id"])
        query_ids = [str(b["_id"])]
        if oid(b["_id"]): query_ids.append(oid(b["_id"]))
        
        hd = col_hd.find_one({"ban_id": {"$in": query_ids}, "trang_thai": "chua_thanhtoan"})
        
        # Tự động đồng bộ lại trạng thái bàn khớp với dữ liệu hóa đơn thực tế
        if hd:
            b["hoa_don"] = hd
            if b["trang_thai"] != "co_khach":
                col_ban.update_one({"_id": b["_id"]}, {"$set": {"trang_thai": "co_khach"}})
                b["trang_thai"] = "co_khach"
        else:
            b["hoa_don"] = None
            if b["trang_thai"] == "co_khach":
                col_ban.update_one({"_id": b["_id"]}, {"$set": {"trang_thai": "trong"}})
                b["trang_thai"] = "trong"
        
    mons = list(col_mon.find({"trang_thai": 1}))
    dms = list(col_dm.find())
    return render_template("index.html", bans=bans, mons=mons, danh_mucs=dms, cai_dat=cd, page_title="Sơ đồ bàn", use_atlas=True)

@app.route("/admin/ban")
def admin_ban():
    cd = get_cd()
    bans = list(col_ban.find().sort("_id", 1))
    edit = col_ban.find_one({"_id": oid(request.args.get("edit"))}) if request.args.get("edit") else None
    return render_template("admin_ban.html", bans=bans, edit_ban=edit, message=request.args.get("msg",""), cai_dat=cd, page_title="Quản lý bàn", use_atlas=True)

@app.route("/admin/ban/add", methods=["POST"])
def admin_ban_add():
    ten = request.form.get("ten_ban","").strip()
    tt = request.form.get("trang_thai","trong")
    eid = request.form.get("id")
    if eid and oid(eid): col_ban.update_one({"_id": oid(eid)}, {"$set": {"ten_ban": ten, "trang_thai": tt}})
    else:
        if ten: col_ban.insert_one({"ten_ban": ten, "trang_thai": tt})
    return redirect("/admin/ban?msg=added")

@app.route("/admin/ban/delete/<id>")
def admin_ban_del(id):
    if oid(id): col_ban.delete_one({"_id": oid(id)})
    return redirect("/admin/ban?msg=deleted")

@app.route("/admin/danh-muc")
def admin_dm():
    cd = get_cd()
    dms = list(col_dm.find().sort("_id", 1))
    for dm in dms: dm["so_luong_mon"] = col_mon.count_documents({"danh_muc_id": str(dm["_id"])})
    edit = col_dm.find_one({"_id": oid(request.args.get("edit"))}) if request.args.get("edit") else None
    return render_template("admin_danh_muc.html", danh_mucs=dms, edit_dm=edit, message=request.args.get("msg",""), cai_dat=cd, page_title="Quản lý danh mục", use_atlas=True)

@app.route("/admin/danh-muc/add", methods=["POST"])
def admin_dm_add():
    ten = request.form.get("ten_danh_muc","").strip()
    eid = request.form.get("id")
    if eid and oid(eid): col_dm.update_one({"_id": oid(eid)}, {"$set": {"ten_danh_muc": ten}})
    else:
        if ten: col_dm.insert_one({"ten_danh_muc": ten})
    return redirect("/admin/danh-muc")

@app.route("/admin/danh-muc/delete/<id>")
def admin_dm_del(id):
    if oid(id):
        if col_mon.count_documents({"danh_muc_id": id}) > 0:
            return redirect("/admin/danh-muc?msg=has_products")
        col_dm.delete_one({"_id": oid(id)})
    return redirect("/admin/danh-muc")

@app.route("/admin/mon")
def admin_mon():
    cd = get_cd()
    mons = list(col_mon.find().sort("_id", -1))
    dm_map = {str(d["_id"]): d["ten_danh_muc"] for d in col_dm.find()}
    for m in mons: m["ten_danh_muc"] = dm_map.get(m.get("danh_muc_id"), "Khác")
    dms = list(col_dm.find())
    edit = col_mon.find_one({"_id": oid(request.args.get("edit"))}) if request.args.get("edit") else None
    return render_template("admin_mon.html", mons=mons, danh_mucs=dms, edit_mon=edit, message=request.args.get("msg",""), cai_dat=cd, page_title="Quản lý thực đơn", use_atlas=True)

@app.route("/admin/mon/add", methods=["POST"])
def admin_mon_add():
    ten = request.form.get("ten_mon","").strip()
    dm_id = request.form.get("danh_muc_id")
    gia = float(request.form.get("gia", 0))
    tt = int(request.form.get("trang_thai", 1))
    eid = request.form.get("id")
    data = {"ten_mon": ten, "danh_muc_id": dm_id, "gia": gia, "trang_thai": tt}
    if eid and oid(eid): col_mon.update_one({"_id": oid(eid)}, {"$set": data})
    else:
        if ten: col_mon.insert_one(data)
    return redirect("/admin/mon")

@app.route("/admin/mon/delete/<id>")
def admin_mon_del(id):
    if oid(id): col_mon.delete_one({"_id": oid(id)})
    return redirect("/admin/mon")

@app.route("/cai-dat", methods=["GET","POST"])
def cai_dat_page():
    cd = get_cd()
    tb=""
    if request.method=="POST":
        ten=request.form.get("ten_quan","").strip()
        if ten:
            col_cd.update_one({"_id": "cau_hinh_1"}, {"$set": {"ten_quan": ten, "dia_chi": request.form.get("dia_chi",""), "dien_thoai": request.form.get("dien_thoai","")}}, upsert=True)
            tb="success"
            cd=get_cd()
    return render_template("cai_dat.html", cai_dat=cd, thong_bao=tb, page_title="Cài đặt", use_atlas=True)

@app.route("/doanh-thu")
def doanh_thu():
    cd = get_cd()
    tu = request.args.get("tu_ngay", datetime.now().strftime("%Y-%m-%d"))
    den = request.args.get("den_ngay", datetime.now().strftime("%Y-%m-%d"))
    ds = []
    for hd in col_hd.find({"trang_thai": "da_thanhtoan"}).sort("ngay_tao", -1):
        ngay = hd.get("ngay_tao_str","")
        if tu <= ngay <= den:
            tong = 0
            for c in col_ct.find({"hoa_don_id": str(hd["_id"])}):
                tong += c["so_luong"] * c["don_gia"]
            hd_fix = {
                "_id": str(hd["_id"]),
                "ban_id": hd.get("ban_id",""),
                "trang_thai": hd.get("trang_thai",""),
                "ngay_tao_str": ngay,
                "tong_tien": tong
            }
            ban = col_ban.find_one({"_id": oid(hd["ban_id"])}) if oid(hd["ban_id"]) else None
            hd_fix["ten_ban"] = ban["ten_ban"] if ban else hd["ban_id"]
            ds.append(hd_fix)
    
    chi_all = {}
    for hd in ds:
        cts = list(col_ct.find({"hoa_don_id": hd["_id"]}))
        ct_fix_list = []
        for ct in cts:
            mon = col_mon.find_one({"_id": oid(ct["san_pham_id"])}) if oid(ct["san_pham_id"]) else None
            ct_fix = {
                "_id": str(ct["_id"]),
                "so_luong": ct.get("so_luong", 0),
                "don_gia": ct.get("don_gia", 0),
                "ten_mon": mon["ten_mon"] if mon else "Món"
            }
            ct_fix_list.append(ct_fix)
        chi_all[hd["_id"]] = ct_fix_list
    
    tong_all = sum([h["tong_tien"] for h in ds])
    return render_template("doanh_thu.html", cai_dat=cd, tong_doanh_thu_loc=tong_all, danh_sach_hd=ds, chi_tiet_all=chi_all, tu_ngay=tu, den_ngay=den, page_title="Doanh thu", use_atlas=True)

# --- API BÁN HÀNG & GỘP BÀN ---
@app.route("/api/ban-trong")
def api_ban_trong():
    try:
        bans = list(col_ban.find({"trang_thai": "trong"}))
        return jsonify([{"id": str(b["_id"]), "ten_ban": b["ten_ban"]} for b in bans])
    except: return jsonify([]), 500

@app.route("/api/ban-co-khach")
def api_ban_co_khach():
    try:
        bans = list(col_ban.find({"trang_thai": "co_khach"}))
        return jsonify([{"id": str(b["_id"]), "ten_ban": b["ten_ban"]} for b in bans])
    except: return jsonify([]), 500

@app.route("/api/mon-by-ban")
def api_mon_by_ban():
    try:
        ban_id = request.args.get("ban_id")
        if not ban_id: return jsonify([])
        
        query_ban_ids = [str(ban_id)]
        if oid(ban_id): query_ban_ids.append(oid(ban_id))
            
        hd = col_hd.find_one({"ban_id": {"$in": query_ban_ids}, "trang_thai": "chua_thanhtoan"})
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

@app.route("/api/thanh-toan", methods=["POST"])
def api_tt():
    try:
        ban_id = str(request.get_json().get("ban_id"))
        query_ban_ids = [ban_id]
        if oid(ban_id): query_ban_ids.append(oid(ban_id))
        
        hd = col_hd.find_one({"ban_id": {"$in": query_ban_ids}, "trang_thai": "chua_thanhtoan"})
        if hd:
            col_hd.update_one({"_id": hd["_id"]}, {"$set": {"trang_thai": "da_thanhtoan", "ngay_tao": datetime.now(), "ngay_tao_str": datetime.now().strftime("%Y-%m-%d")}})
            if oid(ban_id): 
                col_ban.update_one({"_id": oid(ban_id)}, {"$set": {"trang_thai": "trong"}})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/xoa-mon", methods=["POST"])
def api_xoa():
    try:
        cid = request.get_json().get("id")
        if oid(cid): col_ct.delete_one({"_id": oid(cid)})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/gop-ban", methods=["POST"])
def api_gop_ban():
    try:
        d = request.get_json()
        ban_nguon = str(d.get("ban_nguon"))
        ban_dich = str(d.get("ban_dich"))
        
        q_nguon = [ban_nguon]
        if oid(ban_nguon): q_nguon.append(oid(ban_nguon))
        q_dich = [ban_dich]
        if oid(ban_dich): q_dich.append(oid(ban_dich))
        
        hd_nguon = col_hd.find_one({"ban_id": {"$in": q_nguon}, "trang_thai": "chua_thanhtoan"})
        hd_dich = col_hd.find_one({"ban_id": {"$in": q_dich}, "trang_thai": "chua_thanhtoan"})
        
        if not hd_nguon:
            return jsonify({"success": False, "message": "Bàn nguồn không có hóa đơn"})
            
        if not hd_dich:
            # Nếu bàn đích chưa có hóa đơn, đổi luôn bàn của hóa đơn nguồn sang bàn đích
            col_hd.update_one({"_id": hd_nguon["_id"]}, {"$set": {"ban_id": ban_dich}})
            if oid(ban_nguon): col_ban.update_one({"_id": oid(ban_nguon)}, {"$set": {"trang_thai": "trong"}})
            if oid(ban_dich): col_ban.update_one({"_id": oid(ban_dich)}, {"$set": {"trang_thai": "co_khach"}})
            return jsonify({"success": True})
            
        # Nếu cả 2 bàn đều có hóa đơn, gộp chi tiết sang bàn đích và xóa hóa đơn nguồn
        col_ct.update_many({"hoa_don_id": str(hd_nguon["_id"])}, {"$set": {"hoa_don_id": str(hd_dich["_id"])}})
        col_hd.delete_one({"_id": hd_nguon["_id"]})
        if oid(ban_nguon): col_ban.update_one({"_id": oid(ban_nguon)}, {"$set": {"trang_thai": "trong"}})
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("="*60)
    print("QUAN CAFE RACH GIA - MONGODB ATLAS - HOAN CHINH")
    print(f"http://127.0.0.1:{port}")
    print("="*60)
    app.run(host="0.0.0.0", port=port, debug=True)
