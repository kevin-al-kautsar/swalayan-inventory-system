from flask import Flask, jsonify, request
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Inisialisasi Google Sheets API (Mocking/Handling Graceful jika file credentials.json belum ada)
def init_google_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open("Report Waste Swalayan").sheet1
        return sheet
    except Exception as e:
        print(f"Warning: Google Sheets API tidak dapat dihubungi ({e})")
        return None

inventory = {
    "PO-001": {
        "item_name": "Susu UHT 1L",
        "po_qty": 100,
        "received": 0,
        "in_warehouse": 0,
        "on_display": 0,
        "sold": 0,
        "waste": 0
    }
}

waste_logs = []

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}), 200

@app.route('/api/scan', methods=['POST'])
def scan_item():
    data = request.json or {}
    po_id = data.get("po_id")
    action = data.get("action")
    qty = data.get("qty", 1)

    if po_id not in inventory:
        return jsonify({"status": "error", "message": "PO/Barang tidak ditemukan"}), 404

    item = inventory[po_id]

    if action == "receiving":
        item["received"] += qty
    elif action == "warehouse":
        item["in_warehouse"] += qty
    elif action == "display":
        if item["in_warehouse"] >= qty:
            item["in_warehouse"] -= qty
            item["on_display"] += qty
        else:
            return jsonify({"status": "error", "message": "Stok gudang tidak cukup"}), 400
    elif action == "pos":
        if item["on_display"] >= qty:
            item["on_display"] -= qty
            item["sold"] += qty
        else:
            return jsonify({"status": "error", "message": "Stok display tidak cukup"}), 400
    else:
        return jsonify({"status": "error", "message": "Aksi scan tidak valid"}), 400

    return jsonify({"status": "success", "action": action, "data": item}), 200

@app.route('/api/waste', methods=['POST'])
def record_waste():
    data = request.json or {}
    po_id = data.get("po_id")
    qty_waste = data.get("qty", 1)
    reason = data.get("reason", "Expired")

    if po_id not in inventory:
        return jsonify({"status": "error", "message": "Barang tidak ditemukan"}), 404

    item = inventory[po_id]

    if item["on_display"] >= qty_waste:
        item["on_display"] -= qty_waste
    elif item["in_warehouse"] >= qty_waste:
        item["in_warehouse"] -= qty_waste
    else:
        return jsonify({"status": "error", "message": "Stok tidak mencukupi untuk waste"}), 400

    item["waste"] += qty_waste
    timestamp_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = {
        "timestamp": timestamp_now,
        "item_name": item["item_name"],
        "qty": qty_waste,
        "reason": reason
    }
    waste_logs.append(log_entry)

    # Kirim baris baru ke Google Sheets jika koneksi teredia
    sheet = init_google_sheet()
    if sheet:
        try:
            sheet.append_row([timestamp_now, item["item_name"], qty_waste, reason])
        except Exception as e:
            print(f"Gagal append ke sheet: {e}")

    return jsonify({
        "status": "success",
        "message": "Waste berhasil dicatat & diproses ke Spreadsheet",
        "log": log_entry,
        "current_stock": item
    }), 200

@app.route('/api/report/so', methods=['GET'])
def stock_opname_report():
    return jsonify({"status": "success", "stock_opname": inventory, "waste_logs": waste_logs}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)