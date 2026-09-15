from flask import Flask, jsonify, request
import datetime

app = Flask(__name__)

# Memori sementara untuk menyimpan data stok produk swalayan
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

# Log transaksi waste yang nantinya siap dikirim ke Google Sheets
waste_logs = []

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint untuk pemantauan (Monitoring/Logging)"""
    return jsonify({"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}), 200

@app.route('/api/scan', methods=['POST'])
def scan_item():
    """API Otomatisasi Scan Barang: Receiving -> Gudang -> Display -> POS"""
    data = request.json or {}
    po_id = data.get("po_id")
    action = data.get("action")  # 'receiving', 'warehouse', 'display', 'pos'
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
    """API Waste Management (Barang Rusak/Expired)"""
    data = request.json or {}
    po_id = data.get("po_id")
    qty_waste = data.get("qty", 1)
    reason = data.get("reason", "Expired")  # Expired, Rusak, Layu

    if po_id not in inventory:
        return jsonify({"status": "error", "message": "Barang tidak ditemukan"}), 404

    item = inventory[po_id]

    # Potong stok dari display dulu, jika kurang potong dari gudang
    if item["on_display"] >= qty_waste:
        item["on_display"] -= qty_waste
    elif item["in_warehouse"] >= qty_waste:
        item["in_warehouse"] -= qty_waste
    else:
        return jsonify({"status": "error", "message": "Stok tidak mencukupi untuk waste"}), 400

    item["waste"] += qty_waste

    # Catat log waste
    log_entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "item_name": item["item_name"],
        "qty": qty_waste,
        "reason": reason
    }
    waste_logs.append(log_entry)

    return jsonify({
        "status": "success",
        "message": "Waste berhasil dicatat (Ready for Google Sheets API)",
        "log": log_entry,
        "current_stock": item
    }), 200

@app.route('/api/report/so', methods=['GET'])
def stock_opname_report():
    """Laporan Stock Opname Real-time"""
    return jsonify({"status": "success", "stock_opname": inventory, "waste_logs": waste_logs}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)