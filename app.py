from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

client = MongoClient("mongodb://localhost:27017/")
db = client["bmsk_dashboard"]
stations = db["stations"]

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

# -----------------------------
# SUMMARY API
# -----------------------------
@app.route("/api/station-summary")
def station_summary():
    station_type = request.args.get("type", "AWS")
    selected_date = request.args.get("date")

    formatted_date = datetime.strptime(
        selected_date, "%Y-%m-%d"
    ).strftime("%d-%m-%Y")

    pipeline = [
        {
            "$match": {
                "station_type": station_type,
                "recorded_time": formatted_date
            }
        },
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }
        }
    ]

    result = list(stations.aggregate(pipeline))

    working = 0
    not_working = 0

    for r in result:
        if r["_id"] == "Working":
            working = r["count"]
        else:
            not_working += r["count"]

    return jsonify({
        "working": working,
        "not_working": not_working
    })

# -----------------------------
# MAP API (WITH FILTER)
# -----------------------------
@app.route("/api/map-data")
def map_data():
    station_type = request.args.get("type", "AWS")
    selected_date = request.args.get("date")
    status_filter = request.args.get("status")  # ✅ NEW

    formatted_date = datetime.strptime(
        selected_date, "%Y-%m-%d"
    ).strftime("%d-%m-%Y")

    query = {
        "station_type": station_type,
        "recorded_time": formatted_date
    }

    if status_filter in ["Working", "Not Working"]:
        query["status"] = status_filter

    cursor = stations.find(
        query,
        {
            "_id": 0,
            "block": 1,
            "panchayat": 1,
            "district": 1,
            "status": 1,
            "latitude": 1,
            "longitude": 1
        }
    )

    data = []
    for d in cursor:
        if d.get("latitude") and d.get("longitude"):
            data.append({
                "district": d.get("district"),
                "block": d.get("block"),
                "panchayat": d.get("panchayat"),
                "status": d.get("status"),
                "lat": float(d["latitude"]),
                "lon": float(d["longitude"])
            })

    return jsonify(data)

@app.route("/api/company-summary")
def company_summary():
    station_type = request.args.get("type", "AWS")
    selected_date = request.args.get("date")
    status_filter = request.args.get("status")

    formatted_date = datetime.strptime(
        selected_date, "%Y-%m-%d"
    ).strftime("%d-%m-%Y")

    match_stage = {
        "station_type": station_type,
        "recorded_time": formatted_date
    }

    # Status filter (Working / Not Working / All)
    if status_filter in ["Working", "Not Working"]:
        match_stage["status"] = status_filter

    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": "$vendor",   # ✅ COMPANY NAME
                "total": {"$sum": 1},
                "working": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$status", "Working"]}, 1, 0
                        ]
                    }
                },
                "not_working": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$status", "Not Working"]}, 1, 0
                        ]
                    }
                }
            }
        },
        {"$sort": {"_id": 1}}
    ]

    data = []
    for d in stations.aggregate(pipeline):
        data.append({
            "company": d["_id"],        # vendor name
            "total": d["total"],
            "working": d["working"],
            "not_working": d["not_working"]
        })

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)
