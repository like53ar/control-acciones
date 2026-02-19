
# Configuration Constants

DB_FILE = "portfolio.db"
CSV_FILE = "cartera.csv"

# Cache Settings
CACHE_DURATION_SECONDS = 60
SPARKLINE_CACHE_DIR = "sparkline_cache"

# UI Settings
THEME_MODE = "Dark"
COLOR_THEME = "blue"

# Refresh Intervals (ms)
REFRESH_INTERVAL_MAP = {
    "Off": 0,
    "5 min": 5 * 60 * 1000,
    "10 min": 10 * 60 * 1000,
    "15 min": 15 * 60 * 1000
}

# Risk Thresholds (Volatility %)
VOLATILITY_LOW = 1.5
VOLATILITY_HIGH = 3.0

# Retry Settings
API_RETRIES = 3
API_TIMEOUT = 5
