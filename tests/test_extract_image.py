"""Image extraction maps the vision model's JSON into Invoice objects (vision mocked)."""
import app.extract_image as ei


def test_extract_maps_lines(monkeypatch):
    fake = {
        "provider_name": "Snapphoto Care",
        "provider_abn": "12 345 678 901",
        "lines": [
            {"participant": "P1", "item_code": "01_011_0107_1_1",
             "service_date": "2026-05-04", "qty": 2, "unit_price": 72.10,
             "hours": 2, "state": "NSW"},
            {"participant": "P2", "item_code": "", "service_date": "",
             "qty": 1, "unit_price": 0},
        ],
    }
    monkeypatch.setattr(ei, "vision", lambda *a, **k: fake)
    invoices, raw = ei.extract(b"fakeimage", "image/png")
    assert len(invoices) == 2
    assert invoices[0].provider_name == "Snapphoto Care"
    assert invoices[0].provider_abn == "12345678901"   # digits only
    assert invoices[0].item_code == "01_011_0107_1_1"
    assert invoices[0].unit_price == 72.10
    assert invoices[1].state == "NSW"                  # default applied


def test_extract_handles_empty(monkeypatch):
    monkeypatch.setattr(ei, "vision", lambda *a, **k: {"lines": []})
    invoices, raw = ei.extract(b"x", "image/png")
    assert invoices == []


def test_data_uri():
    uri = ei.data_uri(b"abc", "image/jpeg")
    assert uri.startswith("data:image/jpeg;base64,")
