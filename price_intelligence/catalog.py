"""Retail-product taxonomy and verified public-source registry."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetailProduct:
    code: str
    name: str
    normalized_unit: str


RETAIL_PRODUCTS = (
    RetailProduct("raw_milk", "Raw Milk", "liter"),
    RetailProduct("pasteurized_milk", "Pasteurized Milk", "liter"),
    RetailProduct("toned_milk", "Toned Milk", "liter"),
    RetailProduct("full_cream_milk", "Full Cream Milk", "liter"),
    RetailProduct("uht_milk", "UHT Milk", "liter"),
    RetailProduct("smp", "Skim Milk Powder (SMP)", "kg"),
    RetailProduct("wmp", "Whole Milk Powder (WMP)", "kg"),
    RetailProduct("butter", "Butter", "kg"),
    RetailProduct("cheese", "Cheese", "kg"),
    RetailProduct("mozzarella", "Mozzarella", "kg"),
    RetailProduct("cheddar", "Cheddar", "kg"),
    RetailProduct("paneer", "Paneer", "kg"),
    RetailProduct("curd", "Curd", "kg"),
    RetailProduct("yogurt", "Yogurt", "kg"),
    RetailProduct("greek_yogurt", "Greek Yogurt", "kg"),
    RetailProduct("ghee", "Ghee", "kg"),
    RetailProduct("cream", "Cream", "liter"),
    RetailProduct("ice_cream", "Ice Cream", "liter"),
    RetailProduct("whey_powder", "Whey Powder", "kg"),
)

RETAIL_PRODUCT_BY_CODE = {product.code: product for product in RETAIL_PRODUCTS}

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data"
FRANKFURTER_RATES_URL = "https://api.frankfurter.dev/v2/rates"
ECB_DAILY_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

SOURCE_REGISTRY = (
    {
        "name": "U.S. Bureau of Labor Statistics Public Data API",
        "tier": "Official government statistics",
        "coverage": "Configured U.S. consumer-average-price series.",
        "url": "https://www.bls.gov/developers/api_signature_v2.htm",
        "automation": "Public API; series responses include period, value, and source footnotes.",
    },
    {
        "name": "European Central Bank",
        "tier": "Official central-bank reference rates",
        "coverage": "Daily exchange rates based on EUR.",
        "url": ECB_DAILY_RATES_URL,
        "automation": "Public XML reference feed.",
    },
    {
        "name": "Frankfurter",
        "tier": "Central-bank-rate API",
        "coverage": "Current historical currency conversions sourced from central banks.",
        "url": "https://frankfurter.dev/",
        "automation": "No-key public API for display conversions.",
    },
    {
        "name": "Government / official open-data CSV",
        "tier": "Verified by importer metadata",
        "coverage": "Any country where an authorized official source provides a compatible download.",
        "url": "",
        "automation": "Validated local CSV import; source URL, license note, and published date are mandatory.",
    },
)
