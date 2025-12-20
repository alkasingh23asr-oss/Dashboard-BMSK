import requests
import csv
from io import StringIO
from datetime import datetime
from pymongo import MongoClient
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
from dotenv import load_dotenv

# -----------------------------
# LOAD ENV
# -----------------------------
load_dotenv()
BASE_URL = os.getenv("BASE_URL")

# -----------------------------
# MONGO CONNECTION
# -----------------------------
client = MongoClient("mongodb://localhost:27017/")
db = client["bmsk_dashboard"]
collection = db["stations"]

# -----------------------------
# HELPER: FIND LATEST CSV
# -----------------------------
def get_latest_csv_url(station_type):
    response = requests.get(BASE_URL, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    prefix = f"{station_type}_FAULTY"
    links = []

    for a in soup.find_all("a"):
        href = a.get("href")
        if href and href.upper().startswith(prefix):
            links.append(href)

    if not links:
        return None

    def extract_date(name):
        date_part = name.split("_")[-1].replace(".csv", "")
        return datetime.strptime(date_part, "%d%m%Y")

    latest_file = max(links, key=extract_date)
    return urljoin(BASE_URL, latest_file)

# -----------------------------
# FETCH & STORE CSV
# -----------------------------
def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def fetch_and_store(station_type):
    csv_url = get_latest_csv_url(station_type)
    if not csv_url:
        print(f"No CSV found for {station_type}")
        return

    print(f"Fetching {station_type}: {csv_url}")
    csv_text = requests.get(csv_url, timeout=15).text
    reader = csv.DictReader(StringIO(csv_text))

    today = datetime.utcnow().strftime("%Y-%m-%d")

    for row in reader:
        doc = {
    "station_number": row.get("STATION_NUMBER"),
    "station_type": station_type,
    "district": row.get("DISTRICT_NAME"),
    "block": row.get("BLOCK_NAME"),
    "panchayat": row.get("PANCHAYAT_NAME"),
    "latitude": safe_float(row.get("LATITUDE")),
    "longitude": safe_float(row.get("LONGITUDE")),
    "vendor": row.get("VENDOR_NAME"),
    "status": row.get("STATUS"),
    "recorded_time": row.get("RECORDED_TIME"),
    "data_date": today,
    "created_at": datetime.utcnow()
}


        collection.update_one(
            {
                "station_number": doc["station_number"],
                "station_type": station_type,
                "data_date": today
            },
            {"$set": doc},
            upsert=True
        )

    print(f"{station_type} data stored successfully")

# -----------------------------
# RUN FOR BOTH AWS & ARG
# -----------------------------
if __name__ == "__main__":
    fetch_and_store("AWS")
    fetch_and_store("ARG")
