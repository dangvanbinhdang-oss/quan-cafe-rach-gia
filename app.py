import os
from flask import Flask, render_template, request, redirect, jsonify
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import certifi

app = Flask(__name__)
app.secret_key = "cafe_rach_gia_2026"

_default_uri = "mongodb+srv://dangvanbinhdang_db_user:mWpNbVmziJcrvnd3@cluster0.q1apjoi.mongodb.net/cafe_db?retryWrites=true&w=majority&appName=Cluster0"
_env_uri = os.environ.get("MONGO_URI", _default_uri)
if "mongodb.net/?" in _env_uri:
    _env_uri = _env_uri.replace("mongodb.net/?", "mongodb.net/cafe_db?retryWrites=true&w=majority&")
MONGO_URI = _env_uri

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
        b["hoa_don"] = col_hd.find_one({"ban_id": str(b["_id"]), "trang_thai": "chua_thanhtoan"})
    mons = list(col_mon.find({"trang_thai": 1}))
    dms = list(col_dm.find())
    return render_template("index.html", bans=bans, mons=mons, danh_mucs=dms, cai_dat=cd, page_title="Sơ đồ bàn", use_atlas=True)

# ... giữ nguyên các route admin như cũ ...

@app.route("/api/mon-by-ban")
def api_mon_by_ban():
    try:
        ban_id=request.args.get("ban_id")
        hd=col_hd.find_one({"ban_id": ban_id, "trang_thai": "chua_thanhtoan"})
        if not hd: return jsonify({"success":True,"data":[]})
        cts=list(col_ct.find({"hoa_don_id": str(hd["_id"])}))
        data=[]
        for ct in cts:
            mon=col_mon.find_one({"_id": oid(ct["san_pham_id"])})
            data.append({"id": str(ct["_id"]), "ten_mon": mon["ten_mon"] if mon else "?", "so_luong": ct["so_luong"], "don_gia": ct["don_gia"]})
        return jsonify({"success":True,"data":data})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}),500

@app.route("/api/goi-mon", methods=["POST"])
def api_goi_mon():
    try:
        d=request.get_json()
        ban_id=d.get("ban_id"); mon_id=d.get("mon_id"); sl=int(d.get("so_luong",1))
        mon=col_mon.find_one({"_id": oid(mon_id)})
        if not mon: return jsonify({"success":False}),404
        hd=col_hd.find_one({"ban_id": ban_id, "trang_thai": "chua_thanhtoan"})
        if not hd:
            hid=col_hd.insert_one({"ban_id": ban_id, "trang_thai": "chua_thanhtoan", "ngay_tao": datetime.now(), "ngay_tao_str": datetime.now().strftime("%Y-%m-%d")}).inserted_id
            hd={"_id": hid}
            if oid(ban_id): col_ban.update_one({"_id": oid(ban_id)}, {"$set": {"trang_thai": "co_khach"}})
        ex=col_ct.find_one({"hoa_don_id": str(hd["_id"]), "san_pham_id": mon_id})
        if ex: col_ct.update_one({"_id": ex["_id"]}, {"$inc": {"so_luong": sl}})
        else: col_ct.insert_one({"hoa_don_id": str(hd["_id"]), "san_pham_id": mon_id, "so_luong": sl, "don_gia": mon["gia"]})
        return jsonify({"success":True})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}),500

@app.route("/api/thanh-toan", methods=["POST"])
def api_tt():
    try:
        ban_id=request.get_json().get("ban_id")
        hd=col_hd.find_one({"ban_id": ban_id, "trang_thai": "chua_thanhtoan"})
        if hd:
            col_hd.update_one({"_id": hd["_id"]}, {"$set": {"trang_thai": "da_thanhtoan", "ngay_tao": datetime.now(), "ngay_tao_str": datetime.now().strftime("%Y-%m-%d")}})
            if oid(ban_id): col_ban.update_one({"_id": oid(ban_id)}, {"$set": {"trang_thai": "trong"}})
        return jsonify({"success":True})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}),500

@app.route("/api/xoa-mon", methods=["POST"])
def api_xoa():
    try:
        cid=request.get_json().get("id")
        if oid(cid): col_ct.delete_one({"_id": oid(cid)})
        return jsonify({"success":True})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}),500

# ====== TÁCH BÀN - GỘP BÀN MỚI ======
@app.route("/api/ban-trong")
def api_ban_trong():
    bans = list(col_ban.find({"trang_thai": "trong"}).sort("_id", 1))
    return jsonify({"success": True, "data": [{"id": str(b["_id"]), "ten_ban": b["ten_ban"]} for b in bans]})

@app.route("/api/ban-co-khach")
def api_ban_co_khach():
    bans = list(col_ban.find({"trang_thai": "co_khach"}).sort("_id", 1))
    return jsonify({"success": True, "data": [{"id": str(b["_id"]), "ten_ban": b["ten_ban"]} for b in bans]})

@app.route("/api/gop-ban", methods=["POST"])
def api_gop_ban():
    try:
        d = request.get_json()
        ban_dich_id = d.get("ban_dich")
        ban_nguon_ids = d.get("ban_nguon", [])
        hd_dich = col_hd.find_one({"ban_id": ban_dich_id, "trang_thai": "chua_thanhtoan"})
        if not hd_dich:
            hid = col_hd.insert_one({"ban_id": ban_dich_id, "trang_thai": "chua_thanhtoan", "ngay_tao": datetime.now(), "ngay_tao_str": datetime.now().strftime("%Y-%m-%d")}).inserted_id
            hd_dich = {"_id": hid}
            if oid(ban_dich_id): col_ban.update_one({"_id": oid(ban_dich_id)}, {"$set": {"trang_thai": "co_khach"}})
        for src_id in ban_nguon_ids:
            if src_id == ban_dich_id: continue
            hd_src = col_hd.find_one({"ban_id": src_id, "trang_thai": "chua_thanhtoan"})
            if not hd_src: continue
            for ct in list(col_ct.find({"hoa_don_id": str(hd_src["_id"])})):
                ex = col_ct.find_one({"hoa_don_id": str(hd_dich["_id"]), "san_pham_id": ct["san_pham_id"]})
                if ex:
                    col_ct.update_one({"_id": ex["_id"]}, {"$inc": {"so_luong": ct["so_luong"]}})
                    col_ct.delete_one({"_id": ct["_id"]})
                else:
                    col_ct.update_one({"_id": ct["_id"]}, {"$set": {"hoa_don_id": str(hd_dich["_id"])}})
            col_hd.update_one({"_id": hd_src["_id"]}, {"$set": {"trang_thai": "da_thanhtoan"}})
            if oid(src_id): col_ban.update_one({"_id": oid(src_id)}, {"$set": {"trang_thai": "trong"}})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/tach-ban", methods=["POST"])
def api_tach_ban():
    try:
        d = request.get_json()
        ban_nguon_id = d.get("ban_nguon")
        ban_dich_id = d.get("ban_dich")
        chi_tiet_ids = d.get("chi_tiet_ids", [])
        hd_nguon = col_hd.find_one({"ban_id": ban_nguon_id, "trang_thai": "chua_thanhtoan"})
        hd_dich = col_hd.find_one({"ban_id": ban_dich_id, "trang_thai": "chua_thanhtoan"})
        if not hd_dich:
            hid = col_hd.insert_one({"ban_id": ban_dich_id, "trang_thai": "chua_thanhtoan", "ngay_tao": datetime.now(), "ngay_tao_str": datetime.now().strftime("%Y-%m-%d")}).inserted_id
            hd_dich = {"_id": hid}
            if oid(ban_dich_id): col_ban.update_one({"_id": oid(ban_dich_id)}, {"$set": {"trang_thai": "co_khach"}})
        for ct_id in chi_tiet_ids:
            ct = col_ct.find_one({"_id": oid(ct_id), "hoa_don_id": str(hd_nguon["_id"])})
            if not ct: continue
            ex = col_ct.find_one({"hoa_don_id": str(hd_dich["_id"]), "san_pham_id": ct["san_pham_id"]})
            if ex:
                col_ct.update_one({"_id": ex["_id"]}, {"$inc": {"so_luong": ct["so_luong"]}})
                col_ct.delete_one({"_id": ct["_id"]})
            else:
                col_ct.update_one({"_id": ct["_id"]}, {"$set": {"hoa_don_id": str(hd_dich["_id"])}})
        if col_ct.count_documents({"hoa_don_id": str(hd_nguon["_id"])}) == 0:
            col_hd.update_one({"_id": hd_nguon["_id"]}, {"$set": {"trang_thai": "da_thanhtoan"}})
            if oid(ban_nguon_id): col_ban.update_one({"_id": oid(ban_nguon_id)}, {"$set": {"trang_thai": "trong"}})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__=="__main__":
    port=int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
