from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)

# =================================================
# 🔴 EXTERNAL APIs
# =================================================
DAILY_STATUS_API = "http://117.244.242.86:8080/bmskinternal/dailydata/faultydashboard/"
FAULT_STATION_API = "http://117.244.242.86:8080/bmskinternal/dailydata/FS_Report/"


# =================================================
# HELPERS
# =================================================
def fetch_daily_data(station_type, date):
    r = requests.get(
        DAILY_STATUS_API,
        params={"type": station_type, "date": date},
        timeout=30
    )
    r.raise_for_status()
    return r.json()   # list


def fetch_fault_data(station_type, date):
    r = requests.get(
        FAULT_STATION_API,
        params={"type": station_type, "date": date},
        timeout=30
    )
    r.raise_for_status()
    return r.json()   # list


# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")


# ================= SUMMARY =================
@app.route("/api/summary")
def summary():
    t = request.args.get("type")
    date = request.args.get("date")

    data = fetch_daily_data(t, date)

    working = sum(1 for s in data if s.get("status") == "WORKING")
    not_working = sum(1 for s in data if s.get("status") != "WORKING")

    return jsonify({"working": working, "not_working": not_working})


# ================= MAP =================
@app.route("/api/map")
def map_data():
    t = request.args.get("type")
    date = request.args.get("date")
    status = request.args.get("status")

    data = fetch_daily_data(t, date)
    res = []

    for s in data:
        if status != "ALL" and status and s.get("status") != status:
            continue

        if s.get("latitude") and s.get("longitude"):
            res.append({
                "station_id": s.get("station_id"),
                "district": s.get("district"),
                "block": s.get("block"),
                "panchayat": s.get("panchayat"),
                "status": s.get("status"),
                "lat": s.get("latitude"),
                "lon": s.get("longitude")
            })

    return jsonify(res)


# ================= VENDOR SUMMARY =================
@app.route("/api/vendor-summary")
def vendor_summary():
    t = request.args.get("type")
    date = request.args.get("date")

    data = fetch_daily_data(t, date)
    vm = {}

    for s in data:
        v = s.get("vendor")
        if not v:
            continue

        vm.setdefault(v, {
            "vendor": v,
            "total": 0,
            "working": 0,
            "not_working": 0
        })

        vm[v]["total"] += 1
        if s.get("status") == "WORKING":
            vm[v]["working"] += 1
        else:
            vm[v]["not_working"] += 1

    return jsonify(list(vm.values()))


# ================= DISTRICT SUMMARY =================
@app.route("/api/vendor-district-summary")
def vendor_district_summary():
    vendor = request.args.get("vendor")
    status = request.args.get("status")
    t = request.args.get("type")
    date = request.args.get("date")

    data = fetch_daily_data(t, date)
    dm = {}

    for s in data:
        if s.get("vendor") == vendor and s.get("status") == status:
            d = s.get("district")
            dm.setdefault(d, {
                "district": d,
                "total": 0,
                "agency": vendor
            })
            dm[d]["total"] += 1

    return jsonify(sorted(dm.values(), key=lambda x: x["total"], reverse=True))


# ================= BLOCK FAULT (FAULT API) =================
@app.route("/api/block-fault")
def block_fault():
    vendor = request.args.get("vendor")
    district = request.args.get("district")
    t = request.args.get("type")
    date = request.args.get("date")

    data = fetch_fault_data(t, date)
    res = []

    for s in data:
        if s.get("vendor") == vendor and s.get("district") == district:
            f = s.get("fault_data", {})
            res.append({
                "block": s.get("block"),
                "station_id": s.get("station_id"),
                "temp_rh": f.get("temp_rh"),
                "rf": f.get("rf"),
                "ws": f.get("ws"),
                "ap": f.get("ap"),
                "sm": f.get("sm"),
                "sr": f.get("sr"),
                "data_pkt": f.get("data_pkt"),
                "agency": f.get("agency")
            })

    return jsonify(res)


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True, port=8080)
