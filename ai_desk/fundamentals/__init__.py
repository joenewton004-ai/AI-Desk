"""Fundamental stock screener: find great businesses at reasonable prices.

    universe  -> which stocks to look at (large US companies, from Yahoo's screener)
    yahoo     -> download + cache financial statements for each company
    metrics   -> turn statements into ROIC, growth, margins, valuation...
    scoring   -> rank every company against the others and explain why

This is a research tool for TODAY's numbers. It is not a backtest: Yahoo only
has ~4 years of statements and no delisted companies, so judging how such a
screen would have done historically needs point-in-time data (SEC EDGAR).
"""
