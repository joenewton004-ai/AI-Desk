"""Theme maps: where a major capital flow goes, and which links in its supply
chain are likely bottlenecks.

A theme map is a HUMAN-CURATED, DATED INPUT - like a research note, not a
model output. The scan never trusts it blindly: every company it names still
has to show the data fingerprints of a bottleneck (money flowing in, demand
outrunning supply, pricing power) to rank. Edit or add themes here; keep the
`as_of` date and the reasoning current.

Industry names are Yahoo Finance's. `seeds` are notable names that might be
missing from the screen's universe (smaller, or foreign-listed).
"""

from __future__ import annotations

THEMES: dict[str, dict] = {
    "ai_datacenter": {
        "as_of": "2026-10-20",
        "thesis": (
            "Hyperscalers and AI labs are spending hundreds of billions a year on data centres. The chips are "
            "the visible spend, but every GPU also needs electricity, grid connections, transformers, "
            "switchgear, cooling and specialist construction - things that take years to add capacity for. "
            "Those physical constraints, not the chips, are where supply lags demand longest."
        ),
        "demand_signal": "hyperscaler capex guidance (Microsoft, Alphabet, Amazon, Meta, Oracle)",
        "segments": {
            "power_generation": {
                "why": "Data centres need firm 24/7 power; new plants and grid hookups take 3-7 years, so "
                       "existing gas and nuclear fleets gain pricing power (e.g. Vistra, Constellation).",
                "industries": ["Utilities - Independent Power Producers", "Utilities - Renewable",
                               "Utilities - Diversified"],
                "seeds": ["VST", "CEG", "NRG", "TLN"],
            },
            "grid_and_electrical": {
                "why": "Transformers, switchgear and turbines have multi-year lead times and few makers.",
                "industries": ["Electrical Equipment & Parts", "Specialty Industrial Machinery"],
                "seeds": ["GEV", "ETN", "VRT", "HUBB", "POWL"],
            },
            "cooling_and_buildings": {
                "why": "AI racks run far hotter than older servers; liquid cooling capacity is scarce.",
                "industries": ["Building Products & Equipment"],
                "seeds": ["VRT", "MOD", "TT"],
            },
            "construction": {
                "why": "Electrical and mechanical contractors who can build data centres and grid "
                       "connections are booked out for years.",
                "industries": ["Engineering & Construction"],
                "seeds": ["PWR", "EME", "FIX", "MTZ"],
            },
            "networking_and_interconnect": {
                "why": "Clusters of GPUs need very fast networks, optics and connectors.",
                "industries": ["Communication Equipment", "Electronic Components", "Computer Hardware"],
                "seeds": ["ANET", "APH", "CIEN", "COHR"],
            },
            "compute": {
                "why": "Accelerators, memory and chipmaking tools - the most visible (and most crowded) link.",
                "industries": ["Semiconductors", "Semiconductor Equipment & Materials"],
                "seeds": ["NVDA", "AVGO", "MU"],
            },
            "fuel": {
                "why": "Gas pipelines and uranium feed the power plants.",
                "industries": ["Oil & Gas Midstream", "Uranium"],
                "seeds": ["CCJ", "LEU", "WMB"],
            },
        },
    },
}


def theme_industries(name: str) -> dict[str, str]:
    """{industry: segment} for one theme."""
    t = THEMES[name]
    return {ind: seg for seg, s in t["segments"].items() for ind in s["industries"]}


def theme_seeds(name: str) -> dict[str, str]:
    """{ticker: segment} for one theme."""
    t = THEMES[name]
    return {sym: seg for seg, s in t["segments"].items() for sym in s["seeds"]}
