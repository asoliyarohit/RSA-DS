"""Fixed universe, chosen BEFORE any testing: liquid US names across all 11 sectors, incl. laggards and mid-caps.
Survivorship-biased (only names still listed in 2026). No ticker was added/removed after seeing results (GPS, JNPR, MRO, WBA, X dropped only because Yahoo returns no data)."""
ETFS = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "TLT", "GLD"]
STOCKS = [
    # tech / comm
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "AMD", "INTC", "MU", "QCOM", "TXN", "AVGO", "ADBE", "CRM", "ORCL",
    "CSCO", "IBM", "HPQ", "DELL", "NFLX", "PYPL", "EBAY", "T", "VZ", "CMCSA", "DIS", "WDC", "STX", "AMAT", "LRCX",
    "XRX", "AKAM", "SNAP", "TWLO",
    # consumer
    "TSLA", "F", "GM", "NKE", "SBUX", "MCD", "HD", "LOW", "TGT", "WMT", "COST", "KR", "M", "KSS", "BBY", "DG",
    "KO", "PEP", "PG", "CL", "KHC", "GIS", "MO", "PM", "CVS", "MAR", "CCL", "RCL", "NCLH", "HAS", "MAT",
    # financials
    "JPM", "BAC", "C", "WFC", "GS", "MS", "SCHW", "AXP", "COF", "USB", "PNC", "MET", "PRU", "AIG", "ALL", "KEY", "RF",
    # health
    "JNJ", "PFE", "MRK", "ABBV", "BMY", "LLY", "AMGN", "GILD", "UNH", "CI", "MDT", "BSX", "BIIB", "VRTX",
    # industrials / transport
    "BA", "GE", "CAT", "DE", "MMM", "HON", "UPS", "FDX", "LMT", "RTX", "UNP", "DAL", "UAL", "AAL", "LUV",
    # energy / materials / utilities / real estate
    "XOM", "CVX", "COP", "OXY", "SLB", "HAL", "DVN", "APA", "FCX", "NEM", "AA", "CLF", "DOW", "DD",
    "NEE", "DUK", "SO", "AES", "SPG", "AMT", "O",
]
UNIVERSE = ETFS + STOCKS
