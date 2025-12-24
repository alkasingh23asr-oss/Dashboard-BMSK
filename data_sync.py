# data_sync.py
import requests, csv, os
from io import StringIO
from datetime import datetime
from pymongo import MongoClient
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()

FS_AWS_URL = os.getenv("FS_AWS_URL")
BASE_URL = os.getenv("BASE_URL")

client = MongoClient("mongodb://localhost:27017/")
db = client["bmsk_dashboard"]
stations_col = db["stations"]
faulty_col = db["station_faults"]

# ================= UTILS =================
def safe_float(val):
    try:
        return float(val)
    except:
        return None

def normalize_status(raw):
    if not raw:
        return "WORKING"
    raw = raw.strip().upper()
    if raw in ["NOT WORKING", "NON WORKING", "NON-WORKING", "FAULTY"]:
        return "NON-WORKING"
    return "WORKING"

# ================= STATION DATA =================
def get_csv_url_by_date(station_type, date):
    res = requests.get(BASE_URL, timeout=20)
    soup = BeautifulSoup(res.text, "html.parser")

    d = datetime.strptime(date, "%Y-%m-%d").strftime("%d%m%Y")
    prefix = f"{station_type}_FAULTY"

    for a in soup.find_all("a"):
        href = a.get("href")
        if href and href.upper().startswith(prefix) and d in href:
            return urljoin(BASE_URL, href)
    return None

def fetch_and_store_station_data(station_type, date):
    csv_url = get_csv_url_by_date(station_type, date)
    if not csv_url:
        print("CSV not found:", station_type)
        return

    res = requests.get(csv_url, timeout=20)
    reader = csv.DictReader(StringIO(res.text))

    for row in reader:
        doc = {
            "station_id": row.get("STATION_NUMBER"),
            "station_type": station_type,
            "district": row.get("DISTRICT_NAME"),
            "block": row.get("BLOCK_NAME"),
            "panchayat": row.get("PANCHAYAT_NAME"),
            "latitude": safe_float(row.get("LATITUDE")),
            "longitude": safe_float(row.get("LONGITUDE")),
            "vendor": row.get("VENDOR_NAME"),
            "status": normalize_status(row.get("STATUS")),
            "recorded_time": row.get("RECORDED_TIME"),
            "data_date": date,
            "created_at": datetime.utcnow()
        }

        stations_col.update_one(
            {"station_id": doc["station_id"], "station_type": station_type, "data_date": date},
            {"$set": doc},
            upsert=True
        )

# ================= FS FAULT DATA =================
def get_fs_folder(date):
    return datetime.strptime(date, "%Y-%m-%d").strftime("%d%m%Y") + "/"

def fetch_faulty_data(date):
    folder = get_fs_folder(date)
    url = FS_AWS_URL + folder
    res = requests.get(url, timeout=20)
    soup = BeautifulSoup(res.text, "html.parser")

    for a in soup.find_all("a"):
        href = a.get("href")
        if not href or not href.endswith(".csv"):
            continue

        csv_url = url + href
        res_csv = requests.get(csv_url, timeout=20)
        reader = csv.DictReader(StringIO(res_csv.text))

        for row in reader:
            fs = {
                "station_id": row.get("STATION_ID"),
                "temp_rh": row.get("TEMP.RH"),
                "rf": row.get("RF"),
                "ws": row.get("WS"),
                "ap": row.get("AP"),
                "sm": row.get("SM"),
                "sr": row.get("SR"),
                "data_pkt": row.get("DATA_PKT"),
                "agency": row.get("Agency"),
                "data_date": date
            }

            stations_col.update_many(
                {"station_id": fs["station_id"], "status": "NON-WORKING", "data_date": date},
                {"$set": {"fault_data": fs}}
            )

# ================= MAIN JOB =================
def run_daily_sync():
    date = datetime.now().strftime("%Y-%m-%d")
    print("AUTO SYNC START:", date)

    fetch_and_store_station_data("AWS", date)
    fetch_and_store_station_data("ARG", date)
    fetch_faulty_data(date)

    print(" AUTO SYNC DONE")
