import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Pengujian endpoint health check"""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'

def test_scan_receiving(client):
    """Pengujian scan barang masuk (Receiving)"""
    payload = {
        "po_id": "PO-001",
        "action": "receiving",
        "qty": 50
    }
    response = client.post('/api/scan', json=payload)
    assert response.status_code == 200
    assert response.json['data']['received'] == 50

def test_waste_record(client):
    """Pengujian pencatatan waste barang"""
    # Masukkan dulu stok ke receiving dan warehouse
    client.post('/api/scan', json={"po_id": "PO-001", "action": "receiving", "qty": 10})
    client.post('/api/scan', json={"po_id": "PO-001", "action": "warehouse", "qty": 10})
    
    # Catat waste
    payload = {
        "po_id": "PO-001",
        "qty": 2,
        "reason": "Expired"
    }
    response = client.post('/api/waste', json=payload)
    assert response.status_code == 200
    assert response.json['status'] == 'success'