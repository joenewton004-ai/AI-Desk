"""Print 10+ years of SEC-reported history for the companies being researched.

    python research/company_notes_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_desk.fundamentals.edgar import annual_history  # noqa: E402

# ticker -> SEC CIK(s), newest registration first. Verified against data.sec.gov/submissions.
CIKS = {
    "INCY": 879169, "DECK": 910521, "HALO": 1159036, "AU": [1973832, 1067428], "ADBE": 796343,
    "BKNG": 1075531, "NVDA": 1045810, "NBIX": 914475, "BHP": 811809, "FTNT": 1262039,
}


def fmt(h):
    pct = ["revenue_growth", "gross_margin", "operating_margin", "fcf_margin", "roic_pretax"]
    out = h.copy()
    out["revenue_$bn"] = out["revenue_$bn"].map(lambda v: f"{v:.2f}")
    for c in pct:
        out[c] = out[c].map(lambda v: "" if v != v else f"{v:.0%}")
    return out.to_markdown() if hasattr(out, "to_markdown") else out.to_string()


if __name__ == "__main__":
    for t in sys.argv[1:] or CIKS:
        print(f"\n### {t}\n")
        print(annual_history(CIKS[t]).pipe(fmt))
