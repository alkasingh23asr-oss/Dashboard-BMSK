from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from data_sync import run_daily_sync
import atexit


app = Flask(__name__)

# ================= DB =================
client = MongoClient("mongodb://localhost:27017/")
db = client["bmsk_dashboard"]
stations = db["stations"]


# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")


# ================= SUMMARY API =================
@app.route("/api/summary")
def summary():
    station_type = request.args.get("type")
    date = request.args.get("date")

    if not station_type or not date:
        return jsonify({"working": 0, "not_working": 0})

    rec_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")

    pipeline = [
        {"$match": {
            "station_type": station_type,
            "recorded_time": rec_date
        }},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]

    working = 0
    not_working = 0

    for r in stations.aggregate(pipeline):
        if r["_id"] == "WORKING":
            working = r["count"]
        else:
            not_working += r["count"]

    return jsonify({
        "working": working,
        "not_working": not_working
    })


# ================= MAP API =================
@app.route("/api/map")
def map_data():
    station_type = request.args.get("type")
    date = request.args.get("date")
    status = request.args.get("status")

    if not station_type or not date:
        return jsonify([])

    rec_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")

    query = {
        "station_type": station_type,
        "recorded_time": rec_date
    }

    if status and status != "ALL":
        query["status"] = status

    data = []
    for s in stations.find(query, {"_id": 0}):
        if s.get("latitude") and s.get("longitude"):
            data.append({
                "station_id": s.get("station_id"),
                "district": s.get("district"),
                "block": s.get("block"),
                "panchayat": s.get("panchayat"),
                "status": s.get("status"),
                "lat": s.get("latitude"),
                "lon": s.get("longitude")
            })

    return jsonify(data)


# ================= VENDOR SUMMARY =================
@app.route("/api/vendor-summary")
def vendor_summary():
    station_type = request.args.get("type")
    date = request.args.get("date")

    if not station_type or not date:
        return jsonify([])

    rec_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")

    pipeline = [
        {"$match": {
            "station_type": station_type,
            "recorded_time": rec_date,
            "vendor": {"$ne": None}
        }},
        {"$group": {
            "_id": {
                "vendor": "$vendor",
                "status": "$status"
            },
            "count": {"$sum": 1}
        }}
    ]

    vendor_map = {}

    for r in stations.aggregate(pipeline):
        vendor = r["_id"]["vendor"]
        status = r["_id"]["status"]
        count = r["count"]

        vendor_map.setdefault(vendor, {
            "vendor": vendor,
            "total": 0,
            "working": 0,
            "not_working": 0
        })

        vendor_map[vendor]["total"] += count
        if status == "WORKING":
            vendor_map[vendor]["working"] += count
        else:
            vendor_map[vendor]["not_working"] += count

    return jsonify(list(vendor_map.values()))


# ================= DISTRICT SUMMARY =================
@app.route("/api/vendor-district-summary")
def vendor_district_summary():
    vendor = request.args.get("vendor")
    status = request.args.get("status")
    station_type = request.args.get("type")
    date = request.args.get("date")

    if not vendor or not status or not station_type or not date:
        return jsonify([])

    rec_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")

    pipeline = [
        {"$match": {
            "station_type": station_type,
            "recorded_time": rec_date,
            "vendor": vendor,
            "status": status
        }},
        {"$group": {
            "_id": "$district",
            "total": {"$sum": 1},
            "agency": {"$first": "$vendor"}
        }},
        {"$sort": {"total": -1}}
    ]

    return jsonify([
        {
            "district": r["_id"],
            "total": r["total"],
            "agency": r["agency"]
        }
        for r in stations.aggregate(pipeline)
    ])


# ================= BLOCK FAULT =================
@app.route("/api/block-fault")
def block_fault():
    vendor = request.args.get("vendor")
    district = request.args.get("district")
    station_type = request.args.get("type")
    date = request.args.get("date")

    if not vendor or not district or not station_type or not date:
        return jsonify([])

    rec_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")

    query = {
        "station_type": station_type,
        "recorded_time": rec_date,
        "vendor": vendor,
        "district": district,
        "status": "NON-WORKING"
    }

    data = []
    for s in stations.find(query, {"_id": 0}):
        f = s.get("fault_data", {})
        data.append({
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

    return jsonify(data)


# ================= RUN =================
if __name__ == "__main__":
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    scheduler.add_job(
    run_daily_sync,
    trigger="cron",
    hour=11,
    minute=0
    )

    scheduler.start()

    atexit.register(lambda: scheduler.shutdown())
    app.run(debug=False)
