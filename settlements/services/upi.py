"""UPI deep links and the QR code that carries them.

The QR is rendered server-side into a data URI. That keeps the flat's phones
working with no internet and adds no JavaScript library to the page.
"""

from __future__ import annotations

import base64
import io
from decimal import Decimal
from urllib.parse import quote


def upi_link(*, upi_id: str, name: str, amount: Decimal, note: str = "") -> str:
    """A `upi://pay` URI. Tapping it opens GPay / PhonePe / Paytm.

    Returns an empty string when there is no UPI ID, so callers can simply
    check for truthiness rather than juggling None.
    """
    if not upi_id:
        return ""

    params = [
        f"pa={quote(upi_id)}",
        f"pn={quote(name or upi_id)}",
        f"am={amount:.2f}",
        "cu=INR",
    ]
    if note:
        params.append(f"tn={quote(note[:50])}")
    return "upi://pay?" + "&".join(params)


def qr_data_uri(payload: str, *, box_size: int = 8) -> str:
    """PNG data URI for a QR code. Empty string if there is nothing to encode."""
    if not payload:
        return ""

    import qrcode

    code = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=2,
    )
    code.add_data(payload)
    code.make(fit=True)

    image = code.make_image(fill_color="#14161c", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def payment_qr(*, upi_id: str, name: str, amount: Decimal, note: str = "") -> str:
    return qr_data_uri(upi_link(upi_id=upi_id, name=name, amount=amount, note=note))
