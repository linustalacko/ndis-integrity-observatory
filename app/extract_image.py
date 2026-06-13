"""Extract invoice line items from an image (photo/screenshot/PDF page) into the
Invoice schema, so a user can report fraud by snapping a picture.

The vision model returns rows; we map them to Invoice objects and let the same
deterministic engine screen them. Unknown fields become blanks (the engine skips
checks it can't run rather than inventing data).
"""
from __future__ import annotations

import base64

from .claims import Invoice
from .llm import vision

SYSTEM = """You read NDIS invoices and support claims from images. Extract every
line item you can see. Return JSON:
{"provider_name": str, "provider_abn": str (digits only or ""),
 "lines": [{"participant": str, "item_code": str, "service_date": "YYYY-MM-DD",
            "qty": number, "unit_price": number, "hours": number, "state": str}]}.
Rules: copy values exactly as printed; do not guess prices or dates that are not
shown; use "" or null for anything absent. item_code is the NDIS support item
number if present (e.g. 01_011_0107_1_1)."""


def data_uri(content: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(content).decode()}"


def extract(content: bytes, mime: str = "image/png") -> tuple[list[Invoice], dict]:
    data = vision(SYSTEM, "Extract the invoice line items.", data_uri(content, mime))
    provider = data.get("provider_name", "") or "Unknown (from image)"
    abn = "".join(c for c in str(data.get("provider_abn", "")) if c.isdigit())
    invoices = []
    for i, ln in enumerate(data.get("lines", [])):
        invoices.append(Invoice(
            line=i + 1, participant=str(ln.get("participant", "") or ""),
            provider_name=provider, provider_abn=abn,
            item_code=str(ln.get("item_code", "") or ""),
            service_date=str(ln.get("service_date", "") or ""),
            claim_date="", qty=float(ln.get("qty", 1) or 1),
            unit_price=float(ln.get("unit_price", 0) or 0),
            state=str(ln.get("state", "") or "NSW"),
            plan_start="", plan_end="",
            worker_id="", hours=float(ln.get("hours", 0) or 0)))
    return invoices, data
