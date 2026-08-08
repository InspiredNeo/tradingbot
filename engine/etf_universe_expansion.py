"""
Broader ETF candidate list -- real, known ETF tickers across
categories not yet represented in etf_scorer.CANDIDATE_UNIVERSE.
Not a live scrape (no reliable free source available) -- a real,
legitimate list of actual major, liquid ETFs by category.

This is step one: get candidates. Step two (mechanical filter)
uses the real liquidity scorer already built to screen out
anything too thin/short-history before it ever reaches the main
scoring system.
"""

EXPANSION_CANDIDATES = {
    "international_regional": [
        "EWJ",   # Japan
        "EWG",   # Germany
        "EWU",   # UK
        "EWZ",   # Brazil
        "FXI",   # China large-cap
        "INDA",  # India
        "EWY",   # South Korea
        "EWC",   # Canada
        "EWA",   # Australia
        "VWO",   # broad emerging markets (different from EEM)
    ],
    "bond_duration_credit": [
        "SHV",   # ultra-short treasuries
        "IEF",   # 7-10yr treasuries (between SHY and TLT)
        "MBB",   # mortgage-backed securities
        "BND",   # total bond market
        "EMB",   # emerging market bonds
        "HYD",   # high-yield municipal
        "BNDX",  # international bonds
    ],
    "commodities_real_assets": [
        "SLV",   # silver
        "USO",   # oil
        "DBC",   # broad commodities
        "PDBC",  # diversified commodities
        "PICK",  # metals & mining
    ],
    "additional_sectors": [
        "XBI",   # biotech (more focused than XLV)
        "IYT",   # transportation
        "ITB",   # homebuilders
        "KRE",   # regional banks
        "XOP",   # oil & gas exploration
        "SMH",   # semiconductors (alternative to SOXX)
    ],
    "additional_factor_style": [
        "QUAL",  # quality factor
        "SPHQ",  # quality (alternative)
        "SPLV",  # low volatility (alternative to USMV)
        "DGRO",  # dividend growth
    ],
}


def get_all_candidates():
    all_tickers = []
    for category, tickers in EXPANSION_CANDIDATES.items():
        all_tickers.extend(tickers)
    return all_tickers


if __name__ == "__main__":
    all_t = get_all_candidates()
    print(f"Total expansion candidates: {len(all_t)}")
    for category, tickers in EXPANSION_CANDIDATES.items():
        print(f"  {category}: {len(tickers)} tickers")
