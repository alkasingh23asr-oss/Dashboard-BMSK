import requests
import csv
from io import StringIO
from datetime import datetime
from pymongo import MongoClient
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
from dotenv import load_dotenv


# LOAD ENV VARIABLES

load_dotenv()
FS_AWS_URL = os.getenv("FS_AWS_URL")      # FS_Report/AWS/
BASE_URL = os.getenv("BASE_URL")          # faulty dashboard url


# MONGO CONNECTION

client = MongoClient("mongodb://localhost:27017/")
db = client["bmsk_dashboard"]

stations_col = db["stations"]        # PRIMARY
faulty_col = db["station_faults"]    # FS report (raw)


# UTILS

def safe_float(val):
    try:
        return float(val)
    except:
        return None


def normalize_status(raw_status):
    """
    Normalize all status values into:
    WORKING / NON-WORKING
    """
    if not raw_status:
        return "WORKING"

    raw_status = raw_status.strip().upper()

    if raw_status in ["NOT WORKING", "NON WORKING", "NON-WORKING", "FAULTY"]:
        return "NON-WORKING"

    return "WORKING"


# PART 1: FS REPORT (FAULTY SENSOR DATA)

def get_date_directory(manual_date):
    if manual_date:
        folder = datetime.strptime(manual_date, "%Y-%m-%d").strftime("%d%m%Y")
        return folder + "/"

    res = requests.get(FS_AWS_URL, timeout=15)
    soup = BeautifulSoup(res.text, "html.parser")

    folders = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if href and href.endswith("/"):
            try:
                d = datetime.strptime(href.strip("/"), "%d%m%Y")
                folders.append((d, href))
            except:
                pass

    return max(folders, key=lambda x: x[0])[1]


def get_csv_links(folder):
    url = FS_AWS_URL + folder
    res = requests.get(url, timeout=15)
    soup = BeautifulSoup(res.text, "html.parser")

    return [
        url + a.get("href")
        for a in soup.find_all("a")
        if a.get("href", "").endswith(".csv")
    ]


def fetch_faulty_data(csv_url, data_date):
    res = requests.get(csv_url, timeout=15)
    reader = csv.DictReader(StringIO(res.text))
    fs_records = []

    for row in reader:
        fs = {
            "station_id": row["STATION_ID"],
            "temp_rh": row.get("TEMP.RH"),
            "rf": row.get("RF"),
            "ws": row.get("WS"),
            "ap": row.get("AP"),
            "sm": row.get("SM"),
            "sr": row.get("SR"),
            "data_pkt": row.get("DATA_PKT"),
            "agency": row.get("Agency"),
            "source_file": csv_url.split("/")[-1],
            "data_date": data_date,
        }

        faulty_col.update_one(
            {"station_id": fs["station_id"], "data_date": data_date},
            {"$set": fs},
            upsert=True
        )

        fs_records.append(fs)

    return fs_records


# PART 2: STATION STATUS DATA (PRIMARY)

def get_csv_url_by_date(station_type, manual_date=None):
    res = requests.get(BASE_URL, timeout=15)
    soup = BeautifulSoup(res.text, "html.parser")

    prefix = f"{station_type}_FAULTY"
    files = [a.get("href") for a in soup.find_all("a") if a.get("href") and a.get("href").upper().startswith(prefix)]

    if manual_date:
        d = datetime.strptime(manual_date, "%Y-%m-%d").strftime("%d%m%Y")
        for f in files:
            if d in f:
                return urljoin(BASE_URL, f)
        return None

    def extract_date(name):
        return datetime.strptime(name.split("_")[-1].replace(".csv", ""), "%d%m%Y")

    return urljoin(BASE_URL, max(files, key=extract_date))


def fetch_and_store_station_data(station_type, data_date):
    csv_url = get_csv_url_by_date(station_type, data_date)
    if not csv_url:
        return

    res = requests.get(csv_url, timeout=15)
    reader = csv.DictReader(StringIO(res.text))

    for row in reader:
        status = normalize_status(row.get("STATUS"))

        doc = {
            "station_id": row.get("STATION_NUMBER"),
            "station_type": station_type,
            "district": row.get("DISTRICT_NAME"),
            "block": row.get("BLOCK_NAME"),
            "panchayat": row.get("PANCHAYAT_NAME"),
            "latitude": safe_float(row.get("LATITUDE")),
            "longitude": safe_float(row.get("LONGITUDE")),
            "vendor": row.get("VENDOR_NAME"),
            "status": status,
            "recorded_time": row.get("RECORDED_TIME"),
            "data_date": data_date,
            "created_at": datetime.utcnow()
        }

        stations_col.update_one(
            {
                "station_id": doc["station_id"],
                "station_type": station_type,
                "data_date": data_date
            },
            {"$set": doc},
            upsert=True
        )


# PART 3: MERGE FS DATA INTO NON-WORKING STATIONS

def merge_fault_data(fs_records, data_date):
    for fs in fs_records:
        stations_col.update_many(
            {
                "station_id": fs["station_id"],
                "status": "NON-WORKING",
                "data_date": data_date
            },
            {"$set": {"fault_data": fs}}
        )


# MAIN
if __name__ == "__main__":
    try:
        user_input = input("📅 Date (DDMMYYYY) or blank for latest: ").strip()

        if user_input:
            data_date = datetime.strptime(user_input, "%d%m%Y").strftime("%Y-%m-%d")
            manual_date = data_date
        else:
            data_date = datetime.utcnow().strftime("%Y-%m-%d")
            manual_date = None

        print("🚀 STARTING DATA SYNC FOR DATE:", data_date)

        #Station working / non-working
        fetch_and_store_station_data("AWS", data_date)
        fetch_and_store_station_data("ARG", data_date)

        #FS Report
        folder = get_date_directory(manual_date)
        csv_files = get_csv_links(folder)

        fs_records = []
        for csv_file in csv_files:
            fs_records.extend(fetch_faulty_data(csv_file, data_date))

        #Merge FS into NON-WORKING
        merge_fault_data(fs_records, data_date)

        print("DATA SYNC COMPLETED SUCCESSFULLY")

    except Exception as e:
        print("ERROR:", e)
