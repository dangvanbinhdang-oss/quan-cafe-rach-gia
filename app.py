import os
from flask import Flask, render_template, request, redirect, jsonify
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import certifi
import traceback

app = Flask(__name__)
app.secret_key = "cafe_rach_gia_2026"
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://dangvanbinhdang_db_user:mWpNbVmziJcrvnd3@cluster0.q1apjoi.mongodb.net/?appName=Cluster0")

try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), tls=True, serverSelectionTimeoutMS=10000)
    client.admin.command('ping')
    print("✅ ATLAS OK")
except Exception as e:
    print(f"❌ ATLAS: {e}")
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
    try:
        if isinstance(s, ObjectId): return s
        return ObjectId(str(s))
    except: return None

def get_ban_query_ids(ban_id_str):
    ids = [str(ban_id_str)]
    o = oid(ban_id_str)
    if o: ids.append(o)
    return ids

@app.route("/")
def index():
    cd = get_cd()
    bans = list(col_ban.find().sort("ten_ban", 1))
    if not bans:
        col_ban.insert_many([{"ten_ban": f"Bàn {i:02d}", "trang_thai": "trong"} for i in range(1,13)])
        if col_dm.count_documents({}) == 0:
            col_dm.insert_many([{"ten_danh_muc": "Cà phê"}, {"ten_danh_muc": "Trà sữa"}, {"ten_danh_muc": "Đồ Ăn Vặt"}])
        bans = list(col_ban.find().sort("ten_ban", 1))
    for b in bans:
        b["_id_str"] = str(b["_id"])
        hd = col_hd.find_one({"ban_id": {"$in": get_ban_query_ids(b["_id_str"])}, "trang_thai": "chua_thanhtoan"})
        if hd:
            if b.get("trang_thai") != "co_khach":
                col_ban.update_one({"_id": b["_id"]}, {"$set": {"trang_thai": "co_khach"}})
                b["trang_thai"] = "co_khach"
        else:
            if b.get("trang_thai") == "co_khach":
                col_ban.update_one({"_id": b["_id"]}, {"$set": {"trang_thai": "trong"}})
                b["trang_thai"] = "trong"
    mons = list(col_mon.find({"trang_thai": 1}).sort("_id", -1))
    dms = list(col_dm.find())
    return render_template("index.html", bans=bans, mons=mons, danh_mucs=dms, cai_dat=cd, page_title="Sơ đồ bàn")

@app.route("/admin/ban")
def admin_ban():
    cd = get_cd()
    bans = list(col_ban.find().sort("ten_ban", 1))
    edit = col_ban.find_one({"_id": oid(request.args.get("edit"))}) if request.args.get("edit") else None
    return render_template("admin_ban.html", bans=bans, edit_ban=edit, message=request.args.get("msg",""), cai_dat=cd, page_title="Quản lý bàn")

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
    return render_template("admin_danh_muc.html", danh_mucs=dms, edit_dm=edit, message=request.args.get("msg",""), cai_dat=cd, page_title="Quản lý danh mục")

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
        if col_mon.count_documents({"danh_muc_id": id}) > 0: return redirect("/admin/danh-muc?msg=has_products")
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
    return render_template("admin_mon.html", mons=mons, danh_mucs=dms, edit_mon=edit, message=request.args.get("msg",""), cai_dat=cd, page_title="Quản lý thực đơn")

@app.route("/admin/mon/add", methods=["POST"])
def admin_mon_add():
    ten = request.form.get("ten_mon","").strip()
    dm_id = request.form.get("danh_muc_id")
    gia = float(request.form.get("gia", 0) or 0)
    tt = int(request.form.get("trang_thai", 1) or 1)
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
    return render_template("cai_dat.html", cai_dat=cd, thong_bao=tb, page_title="Cài đặt")

# ==================== DOANH THU - BẢN ĐÚNG CHO TEMPLATE CỦA BẠN ====================
@app.route("/doanh-thu")
def doanh_thu():
    cd = get_cd()
    tu_ngay = request.args.get("tu_ngay", datetime.now().strftime("%Y-%m-%d"))
    den_ngay = request.args.get("den_ngay", datetime.now().strftime("%Y-%m-%d"))
    hom_nay_str = datetime.now().strftime("%Y-%m-%d")
    thang_prefix = datetime.now().strftime("%Y-%m")

    danh_sach_hd = []
    chi_tiet_all = {}
    tong_doanh_thu_loc = 0
    dt_hom_nay = 0
    dt_thang_nay = 0

    try:
        all_hd = list(col_hd.find({"trang_thai": "da_thanhtoan"}))
        for hd in all_hd:
            ngay_str = hd.get("ngay_tao_str", "")
            if not ngay_str and hd.get("ngay_tao"):
                try: ngay_str = hd["ngay_tao"].strftime("%Y-%m-%d")
                except: ngay_str = hom_nay_str
            if not ngay_str: continue

            # tính tổng
            tong = 0
            cts = list(col_ct.find({"hoa_don_id": str(hd["_id"])}))
            for c in cts:
                try: tong += int(c.get("so_luong",0)) * float(c.get("don_gia",0))
                except: pass

            # cộng dồn hôm nay / tháng này
            if ngay_str == hom_nay_str:
                dt_hom_nay += tong
            if ngay_str.startswith(thang_prefix):
                dt_thang_nay += tong

            # lọc theo khoảng user chọn
            if not (tu_ngay <= ngay_str <= den_ngay):
                continue

            ten_ban = str(hd.get("ban_id",""))
            if oid(hd.get("ban_id")):
                b = col_ban.find_one({"_id": oid(hd["ban_id"])})
                if b: ten_ban = b.get("ten_ban", ten_ban)

            hd_id_str = str(hd["_id"])
            danh_sach_hd.append({
                "_id": hd_id_str,
                "ten_ban": ten_ban,
                "ngay_tao_str": ngay_str,
                "tong_tien": tong
            })
            tong_doanh_thu_loc += tong

            lst = []
            for ct in cts:
                ten_mon = "Món"
                if oid(ct.get("san_pham_id")):
                    m = col_mon.find_one({"_id": oid(ct["san_pham_id"])})
                    if m: ten_mon = m.get("ten_mon", ten_mon)
                lst.append({
                    "ten_mon": ten_mon,
                    "so_luong": ct.get("so_luong",0),
                    "don_gia": ct.get("don_gia",0)
                })
            chi_tiet_all[hd_id_str] = lst

        danh_sach_hd.sort(key=lambda x: x["ngay_tao_str"], reverse=True)

    except Exception as e:
        print("LOI DOANH THU:", e)
        traceback.print_exc()

    return render_template("doanh_thu.html",
        cai_dat=cd,
        tu_ngay=tu_ngay,
        den_ngay=den_ngay,
        dt_hom_nay=dt_hom_nay,
        dt_thang_nay=dt_thang_nay,
        tong_doanh_thu_loc=tong_doanh_thu_loc,
        danh_sach_hd=danh_sach_hd,
        chi_tiet_all=chi_tiet_all,
        page_title="Doanh thu"
    )

# API
@app.route("/api/ban-trong")
def api_ban_trong():
    bans = list(col_ban.find({"trang_thai": "trong"}).sort("ten_ban", 1))
    return jsonify([{"id": str(b["_id"]), "ten_ban": b["ten_ban"], "trang_thai": b["trang_thai"]} for b in bans])

@app.route("/api/ban-co-khach")
def api_ban_co_khach():
    bans = list(col_ban.find({"trang_thai": "co_khach"}).sort("ten_ban", 1))
    return jsonify([{"id": str(b["_id"]), "ten_ban": b["ten_ban"], "trang_thai": b["trang_thai"]} for b in bans])

@app.route("/api/mon-by-ban")
def api_mon_by_ban():
    ban_id = request.args.get("ban_id")
    if not ban_id: return jsonify([])
    hd = col_hd.find_one({"ban_id": {"$in": get_ban_query_ids(ban_id)}, "trang_thai": "chua_thanhtoan"})
    if not hd: return jsonify([])
    data=[]
    for ct in list(col_ct.find({"hoa_don_id": str(hd["_id"])})):
        mon = col_mon.find_one({"_id": oid(ct["san_pham_id"])}) if oid(ct["san_pham_id"]) else None
        data.append({"id": str(ct["_id"]), "ten_mon": mon["ten_mon"] if mon else "Món", "so_luong": ct["so_luong"], "gia": ct["don_gia"]})
    return jsonify(data)

@app.route("/api/goi-mon", methods=["POST"])
def api_goi_mon():
    d=request.get_json()
    ban_id=str(d.get("ban_id")); mon_id=d.get("mon_id"); sl=int(d.get("so_luong",1))
    mon=col_mon.find_one({"_id": oid(mon_id)})
    if not mon: return jsonify({"success": False, "message": "Không tìm thấy món"}), 404
    hd=col_hd.find_one({"ban_id": {"$in": get_ban_query_ids(ban_id)}, "trang_thai": "chua_thanhtoan"})
    if not hd:
        hid=col_hd.insert_one({"ban_id": ban_id, "trang_thai": "chua_thanhtoan", "ngay_tao": datetime.now(), "ngay_tao_str": datetime.now().strftime("%Y-%m-%d")}).inserted_id
        hd={"_id": hid}
        if oid(ban_id): col_ban.update_one({"_id": oid(ban_id)}, {"$set": {"trang_thai": "co_khach"}})
    ex=col_ct.find_one({"hoa_don_id": str(hd["_id"]), "san_pham_id": mon_id})
    if ex: col_ct.update_one({"_id": ex["_id"]}, {"$inc": {"so_luong": sl}})
    else: col_ct.insert_one({"hoa_don_id": str(hd["_id"]), "san_pham_id": mon_id, "so_luong": sl, "don_gia": mon["gia"]})
    return jsonify({"success": True})

@app.route("/api/thanh-toan", methods=["POST"])
def api_tt():
    ban_id=str(request.get_json().get("ban_id"))
    hd=col_hd.find_one({"ban_id": {"$in": get_ban_query_ids(ban_id)}, "trang_thai": "chua_thanhtoan"})
    if hd:
        col_hd.update_one({"_id": hd["_id"]}, {"$set": {"trang_thai": "da_thanhtoan", "ngay_tao": datetime.now(), "ngay_tao_str": datetime.now().strftime("%Y-%m-%d")}})
        if oid(ban_id): col_ban.update_one({"_id": oid(ban_id)}, {"$set": {"trang_thai": "trong"}})
    return jsonify({"success": True})

@app.route("/api/xoa-mon", methods=["POST"])
def api_xoa():
    cid=request.get_json().get("id")
    if oid(cid): col_ct.delete_one({"_id": oid(cid)})
    return jsonify({"success": True})

@app.route("/api/gop-ban", methods=["POST"])
def api_gop_ban():
    d=request.get_json()
    ban_nguon=str(d.get("ban_nguon")); ban_dich=str(d.get("ban_dich"))
    if ban_nguon==ban_dich: return jsonify({"success": False, "message": "Không thể gộp trùng bàn!"})
    hd_nguon=col_hd.find_one({"ban_id": {"$in": get_ban_query_ids(ban_nguon)}, "trang_thai": "chua_thanhtoan"})
    hd_dich=col_hd.find_one({"ban_id": {"$in": get_ban_query_ids(ban_dich)}, "trang_thai": "chua_thanhtoan"})
    if not hd_nguon: return jsonify({"success": False, "message": "Bàn nguồn trống"})
    if not hd_dich:
        col_hd.update_one({"_id": hd_nguon["_id"]}, {"$set": {"ban_id": ban_dich}})
        if oid(ban_nguon): col_ban.update_one({"_id": oid(ban_nguon)}, {"$set": {"trang_thai": "trong"}})
        if oid(ban_dich): col_ban.update_one({"_id": oid(ban_dich)}, {"$set": {"trang_thai": "co_khach"}})
        return jsonify({"success": True})
    for ct in list(col_ct.find({"hoa_don_id": str(hd_nguon["_id"])})):
        ct_d=col_ct.find_one({"hoa_don_id": str(hd_dich["_id"]), "san_pham_id": ct["san_pham_id"]})
        if ct_d:
            col_ct.update_one({"_id": ct_d["_id"]}, {"$inc": {"so_luong": ct["so_luong"]}})
            col_ct.delete_one({"_id": ct["_id"]})
        else:
            col_ct.update_one({"_id": ct["_id"]}, {"$set": {"hoa_don_id": str(hd_dich["_id"])}})
    col_hd.delete_one({"_id": hd_nguon["_id"]})
    if oid(ban_nguon): col_ban.update_one({"_id": oid(ban_nguon)}, {"$set": {"trang_thai": "trong"}})
    return jsonify({"success": True})

@app.route("/api/tach-ban", methods=["POST"])
def api_tach_ban():
    d=request.get_json()
    ban_nguon=str(d.get("ban_nguon")); ban_dich=str(d.get("ban_dich")); mon_chuyen=d.get("mon_chuyen",[])
    if ban_nguon==ban_dich: return jsonify({"success": False, "message": "Không thể tách cùng 1 bàn"})
    hd_nguon=col_hd.find_one({"ban_id": {"$in": get_ban_query_ids(ban_nguon)}, "trang_thai": "chua_thanhtoan"})
    if not hd_nguon: return jsonify({"success": False, "message": "Bàn nguồn trống"})
    hd_dich=col_hd.find_one({"ban_id": {"$in": get_ban_query_ids(ban_dich)}, "trang_thai": "chua_thanhtoan"})
    if not hd_dich:
        hid=col_hd.insert_one({"ban_id": ban_dich, "trang_thai": "chua_thanhtoan", "ngay_tao": datetime.now(), "ngay_tao_str": datetime.now().strftime("%Y-%m-%d")}).inserted_id
        hd_dich={"_id": hid}
        if oid(ban_dich): col_ban.update_one({"_id": oid(ban_dich)}, {"$set": {"trang_thai": "co_khach"}})
    for item in mon_chuyen:
        ct=col_ct.find_one({"_id": oid(item.get("id"))})
        if not ct: continue
        sl=int(item.get("so_luong",1))
        if sl>=ct["so_luong"]:
            ct_tr=col_ct.find_one({"hoa_don_id": str(hd_dich["_id"]), "san_pham_id": ct["san_pham_id"]})
            if ct_tr:
                col_ct.update_one({"_id": ct_tr["_id"]}, {"$inc": {"so_luong": ct["so_luong"]}})
                col_ct.delete_one({"_id": ct["_id"]})
            else:
                col_ct.update_one({"_id": ct["_id"]}, {"$set": {"hoa_don_id": str(hd_dich["_id"])}})
        else:
            col_ct.update_one({"_id": ct["_id"]}, {"$inc": {"so_luong": -sl}})
            ct_tr=col_ct.find_one({"hoa_don_id": str(hd_dich["_id"]), "san_pham_id": ct["san_pham_id"]})
            if ct_tr: col_ct.update_one({"_id": ct_tr["_id"]}, {"$inc": {"so_luong": sl}})
            else: col_ct.insert_one({"hoa_don_id": str(hd_dich["_id"]), "san_pham_id": ct["san_pham_id"], "so_luong": sl, "don_gia": ct["don_gia"]})
    if col_ct.count_documents({"hoa_don_id": str(hd_nguon["_id"])})==0:
        col_hd.delete_one({"_id": hd_nguon["_id"]})
        if oid(ban_nguon): col_ban.update_one({"_id": oid(ban_nguon)}, {"$set": {"trang_thai": "trong"}})
    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
