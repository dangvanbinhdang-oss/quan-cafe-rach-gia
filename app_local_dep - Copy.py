
from flask import Flask, render_template, request, redirect, jsonify
from datetime import datetime
import os, json, uuid
app = Flask(__name__)
DATA_FILE = "data.json"
def load_data():
    if not os.path.exists(DATA_FILE):
        data = {"cai_dat": {"ten_quan": "QUÁN CAFE RẠCH GIÁ", "dia_chi": "TP. Rạch Giá, Kiên Giang", "dien_thoai": "0909 123 456"}, "ban_an": [{"_id": f"ban{i:02d}", "ten_ban": f"Bàn {i:02d}", "trang_thai": "trong"} for i in range(1,7)], "danh_muc": [{"_id": "dm1", "ten_danh_muc": "Cà phê"}, {"_id": "dm2", "ten_danh_muc": "Trà sữa"}], "san_pham": [{"_id": "mon1", "ten_mon": "Cà phê sữa đá", "danh_muc_id": "dm1", "gia": 25000, "trang_thai": 1}], "hoa_don": [], "chi_tiet_hoa_don": []}
        json.dump(data, open(DATA_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        return data
    return json.load(open(DATA_FILE,"r",encoding="utf-8"))
def save_data(d): json.dump(d, open(DATA_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
def find_by_id(lst,_id):
    for x in lst:
        if x["_id"]==_id: return x
    return None
@app.route("/")
def index():
    data=load_data()
    bans=data["ban_an"]
    for b in bans: b["hoa_don"]=next((hd for hd in data["hoa_don"] if hd["ban_id"]==b["_id"] and hd["trang_thai"]=="chua_thanhtoan"),None)
    mons=[m for m in data["san_pham"] if m["trang_thai"]==1]
    return render_template("index.html", bans=bans, mons=mons, danh_mucs=data["danh_muc"], cai_dat=data["cai_dat"], page_title="Sơ đồ bàn")
@app.route("/admin/ban")
def admin_ban():
    data=load_data()
    edit=find_by_id(data["ban_an"], request.args.get("edit")) if request.args.get("edit") else None
    return render_template("admin_ban.html", bans=data["ban_an"], edit_ban=edit, message=request.args.get("msg",""), cai_dat=data["cai_dat"], page_title="Quản lý bàn")
@app.route("/admin/ban/add", methods=["POST"])
def admin_ban_add():
    data=load_data()
    ten=request.form.get("ten_ban","").strip()
    tt=request.form.get("trang_thai","trong")
    eid=request.form.get("id")
    if eid:
        b=find_by_id(data["ban_an"],eid)
        if b: b.update({"ten_ban":ten,"trang_thai":tt})
    else:
        if ten: data["ban_an"].append({"_id": str(uuid.uuid4())[:8], "ten_ban":ten,"trang_thai":tt})
    save_data(data)
    return redirect("/admin/ban?msg=added")
@app.route("/admin/ban/delete/<id>")
def admin_ban_del(id):
    data=load_data()
    data["ban_an"]=[b for b in data["ban_an"] if b["_id"]!=id]
    save_data(data)
    return redirect("/admin/ban?msg=deleted")
@app.route("/admin/ban/status/<id>/<status>")
def admin_ban_status(id,status):
    data=load_data()
    b=find_by_id(data["ban_an"],id)
    if b: b["trang_thai"]=status
    save_data(data)
    return redirect("/admin/ban?msg=status_updated")
@app.route("/admin/danh-muc")
def admin_dm():
    data=load_data()
    for dm in data["danh_muc"]: dm["so_luong_mon"]=len([m for m in data["san_pham"] if m.get("danh_muc_id")==dm["_id"]])
    edit=find_by_id(data["danh_muc"], request.args.get("edit")) if request.args.get("edit") else None
    return render_template("admin_danh_muc.html", danh_mucs=data["danh_muc"], edit_dm=edit, message=request.args.get("msg",""), cai_dat=data["cai_dat"], page_title="Quản lý danh mục")
@app.route("/admin/danh-muc/add", methods=["POST"])
def admin_dm_add():
    data=load_data()
    ten=request.form.get("ten_danh_muc","").strip()
    eid=request.form.get("id")
    if eid:
        dm=find_by_id(data["danh_muc"],eid)
        if dm: dm["ten_danh_muc"]=ten
    else:
        if ten: data["danh_muc"].append({"_id": str(uuid.uuid4())[:8], "ten_danh_muc":ten})
    save_data(data)
    return redirect("/admin/danh-muc")
@app.route("/admin/danh-muc/delete/<id>")
def admin_dm_del(id):
    data=load_data()
    data["danh_muc"]=[d for d in data["danh_muc"] if d["_id"]!=id]
    save_data(data)
    return redirect("/admin/danh-muc")
@app.route("/admin/mon")
def admin_mon():
    data=load_data()
    dm_map={d["_id"]: d["ten_danh_muc"] for d in data["danh_muc"]}
    for m in data["san_pham"]: m["ten_danh_muc"]=dm_map.get(m.get("danh_muc_id"),"Khác")
    edit=find_by_id(data["san_pham"], request.args.get("edit")) if request.args.get("edit") else None
    return render_template("admin_mon.html", mons=data["san_pham"], danh_mucs=data["danh_muc"], edit_mon=edit, message=request.args.get("msg",""), cai_dat=data["cai_dat"], page_title="Quản lý món")
@app.route("/admin/mon/add", methods=["POST"])
def admin_mon_add():
    data=load_data()
    ten=request.form.get("ten_mon","").strip()
    dm_id=request.form.get("danh_muc_id")
    gia=float(request.form.get("gia",0))
    tt=int(request.form.get("trang_thai",1))
    eid=request.form.get("id")
    if eid:
        m=find_by_id(data["san_pham"],eid)
        if m: m.update({"ten_mon":ten,"danh_muc_id":dm_id,"gia":gia,"trang_thai":tt})
    else:
        if ten: data["san_pham"].append({"_id": str(uuid.uuid4())[:8], "ten_mon":ten,"danh_muc_id":dm_id,"gia":gia,"trang_thai":tt})
    save_data(data)
    return redirect("/admin/mon")
@app.route("/admin/mon/delete/<id>")
def admin_mon_del(id):
    data=load_data()
    data["san_pham"]=[m for m in data["san_pham"] if m["_id"]!=id]
    save_data(data)
    return redirect("/admin/mon")
@app.route("/admin/mon/status/<id>/<int:status>")
def admin_mon_status(id,status):
    data=load_data()
    m=find_by_id(data["san_pham"],id)
    if m: m["trang_thai"]=status
    save_data(data)
    return redirect("/admin/mon")
@app.route("/cai-dat", methods=["GET","POST"])
def cai_dat_page():
    data=load_data()
    tb=""
    if request.method=="POST":
        ten=request.form.get("ten_quan","").strip()
        if ten:
            data["cai_dat"].update({"ten_quan":ten,"dia_chi":request.form.get("dia_chi",""),"dien_thoai":request.form.get("dien_thoai","")})
            save_data(data)
            tb="success"
    return render_template("cai_dat.html", cai_dat=data["cai_dat"], thong_bao=tb, page_title="Cài đặt")
@app.route("/doanh-thu")
def doanh_thu():
    data=load_data()
    tu=request.args.get("tu_ngay", datetime.now().strftime("%Y-%m-%d"))
    den=request.args.get("den_ngay", datetime.now().strftime("%Y-%m-%d"))
    ds=[]
    for hd in data["hoa_don"]:
        if hd["trang_thai"]!="da_thanhtoan": continue
        if tu<=hd.get("ngay_tao_str","")<=den:
            hd["tong_tien"]=sum([c["so_luong"]*c["don_gia"] for c in data["chi_tiet_hoa_don"] if c["hoa_don_id"]==hd["_id"]])
            ban=find_by_id(data["ban_an"], hd["ban_id"])
            hd["ten_ban"]=ban["ten_ban"] if ban else hd["ban_id"]
            ds.append(hd)
    chi_all={}
    for hd in ds:
        cts=[c for c in data["chi_tiet_hoa_don"] if c["hoa_don_id"]==hd["_id"]]
        for ct in cts:
            mon=find_by_id(data["san_pham"], ct["san_pham_id"])
            ct["ten_mon"]=mon["ten_mon"] if mon else "Món"
        chi_all[hd["_id"]]=cts
    return render_template("doanh_thu.html", cai_dat=data["cai_dat"], dt_hom_nay=0, dt_thang_nay=0, tong_doanh_thu_loc=sum([h["tong_tien"] for h in ds]), danh_sach_hd=ds, chi_tiet_all=chi_all, tu_ngay=tu, den_ngay=den, page_title="Doanh thu")
@app.route("/api/mon-by-ban")
def api_mon_by_ban():
    data=load_data()
    ban_id=request.args.get("ban_id")
    hd=next((h for h in data["hoa_don"] if h["ban_id"]==ban_id and h["trang_thai"]=="chua_thanhtoan"),None)
    if not hd: return jsonify({"success":True,"data":[]})
    cts=[c for c in data["chi_tiet_hoa_don"] if c["hoa_don_id"]==hd["_id"]]
    for ct in cts:
        mon=find_by_id(data["san_pham"], ct["san_pham_id"])
        ct["ten_mon"]=mon["ten_mon"] if mon else "?"
        ct["id"]=ct["_id"]
    return jsonify({"success":True,"data":cts})
@app.route("/api/goi-mon", methods=["POST"])
def api_goi_mon():
    data=load_data()
    d=request.get_json()
    ban_id=d.get("ban_id"); mon_id=d.get("mon_id"); sl=int(d.get("so_luong",1))
    hd=next((h for h in data["hoa_don"] if h["ban_id"]==ban_id and h["trang_thai"]=="chua_thanhtoan"),None)
    if not hd:
        hd={"_id": str(uuid.uuid4())[:8], "ban_id":ban_id,"trang_thai":"chua_thanhtoan","ngay_tao_str":datetime.now().strftime("%Y-%m-%d")}
        data["hoa_don"].append(hd)
        b=find_by_id(data["ban_an"],ban_id)
        if b: b["trang_thai"]="co_khach"
    ex=next((c for c in data["chi_tiet_hoa_don"] if c["hoa_don_id"]==hd["_id"] and c["san_pham_id"]==mon_id),None)
    if ex: ex["so_luong"]+=sl
    else:
        mon=find_by_id(data["san_pham"],mon_id)
        data["chi_tiet_hoa_don"].append({"_id": str(uuid.uuid4())[:8], "hoa_don_id":hd["_id"],"san_pham_id":mon_id,"so_luong":sl,"don_gia":mon["gia"] if mon else 0})
    save_data(data)
    return jsonify({"success":True})
@app.route("/api/thanh-toan", methods=["POST"])
def api_tt():
    data=load_data()
    ban_id=request.get_json().get("ban_id")
    hd=next((h for h in data["hoa_don"] if h["ban_id"]==ban_id and h["trang_thai"]=="chua_thanhtoan"),None)
    if hd:
        hd["trang_thai"]="da_thanhtoan"
        hd["ngay_tao_str"]=datetime.now().strftime("%Y-%m-%d")
        b=find_by_id(data["ban_an"],ban_id)
        if b: b["trang_thai"]="trong"
    save_data(data)
    return jsonify({"success":True})
@app.route("/api/xoa-mon", methods=["POST"])
def api_xoa():
    data=load_data()
    cid=request.get_json().get("id")
    data["chi_tiet_hoa_don"]=[c for c in data["chi_tiet_hoa_don"] if c["_id"]!=cid]
    save_data(data)
    return jsonify({"success":True})
if __name__=="__main__":
    print("QUAN CAFE RACH GIA - BAN DEP TIENG VIET - KHONG CAN MONGODB - 100% KHONG LOI SSL")
    app.run(debug=True, port=5000)
