from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict

from megamakmur.models import ArbitrageValuation, VehicleListing


def verify_fonnte_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    """Verifies HMAC-SHA256 webhook signature from Fonnte WhatsApp gateway."""
    if not signature_header or not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.strip())


def format_whatsapp_scouting_alert(listing: VehicleListing, valuation: ArbitrageValuation) -> str:
    """
    Generates a structured WhatsApp alert payload for field inspectors
    in Jabodetabek via Fonnte API.
    """
    star = "⭐ " if "WINDFALL" in listing.windfall_flag.upper() else ""
    credit_label = f"Ya ({listing.leasing_partner})" if listing.credit_eligible else "Tidak (Wajib Cash)"

    lines = [
        f"*{star}[RADAR MEGA MAKMUR] {valuation.unit_name}*",
        f"• *ID / Tier:* `{listing.unit_id}` ({listing.tier.value})",
        f"• *Lokasi & Plat:* {listing.plate_location}",
        f"• *Harga Iklan:* Rp {listing.ask_price_idr:,.0f}",
        f"• *Target Beli / Mentok:* Rp {listing.target_buy_idr:,.0f} (Max: Rp {listing.walk_away_idr:,.0f})",
        f"• *Rencana Variasi (HPP):* {listing.variation_plan} (Rp {listing.recon_hpp_idr:,.0f})",
        f"• *Target Jual Bersih:* Rp {listing.target_exit_idr:,.0f}",
        f"• *Est. Laba Bersih:* Rp {valuation.net_profit_at_target_idr:,.0f} (ROI {valuation.roi_at_target_pct:.1f}%)",
        f"• *Kelayakan Kredit:* {credit_label}",
        f"• *Risiko & Cek Fisik:* [{listing.windfall_flag}] {listing.risk_notes}",
        f"• *Rekomendasi Mesin:* `{valuation.recommendation}` (Alpha: {valuation.composite_alpha_score})",
        f"• *Link:* {listing.listing_url}",
    ]
    return "\n".join(lines)


def build_fonnte_dispatch_payload(
    target_phone: str,
    listing: VehicleListing,
    valuation: ArbitrageValuation,
) -> Dict[str, Any]:
    """Constructs the JSON request body for Fonnte `/send` endpoint."""
    normalized = target_phone.strip().replace(" ", "").replace("-", "")
    if normalized.startswith("08"):
        normalized = "62" + normalized[1:]
    elif normalized.startswith("+62"):
        normalized = normalized[1:]

    return {
        "target": normalized,
        "message": format_whatsapp_scouting_alert(listing, valuation),
        "countryCode": "62",
        "typing": False,
    }
