"""Source configuration and commodity taxonomy for official data imports."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DairyProduct:
    code: str
    name: str
    hs_code: str
    aliases: tuple[str, ...]
    food_balance_items: tuple[str, ...]
    production_types: tuple[str, ...] = ()


DAIRY_PRODUCTS = (
    DairyProduct(
        "liquid_milk",
        "Liquid Milk & Cream",
        "0401",
        ("liquid milk", "raw milk", "milk and cream"),
        ("Milk - Excluding Butter",),
        ("Total milk",),
    ),
    DairyProduct(
        "milk_powder",
        "Milk Powder",
        "0402",
        ("milk powder", "powder"),
        ("Milk - Excluding Butter",),
    ),
    DairyProduct(
        "smp",
        "Skimmed Milk Powder (SMP)",
        "040210",
        ("smp", "skimmed milk powder"),
        ("Milk - Excluding Butter",),
    ),
    DairyProduct(
        "wmp",
        "Whole Milk Powder (WMP)",
        "040221",
        ("wmp", "whole milk powder"),
        ("Milk - Excluding Butter",),
    ),
    DairyProduct(
        "butter",
        "Butter",
        "040510",
        ("butter",),
        ("Butter, Ghee",),
    ),
    DairyProduct(
        "cheese",
        "Cheese",
        "0406",
        ("cheese",),
        ("Cheese",),
    ),
    DairyProduct(
        "whey_powder",
        "Whey Powder",
        "040410",
        ("whey powder", "whey"),
        ("Whey",),
    ),
    DairyProduct(
        "ghee",
        "Ghee",
        "040590",
        ("ghee",),
        ("Butter, Ghee",),
    ),
    DairyProduct(
        "cream",
        "Cream",
        "040150",
        ("cream",),
        ("Cream",),
    ),
    DairyProduct(
        "yogurt",
        "Yogurt",
        "040310",
        ("yogurt", "yoghurt"),
        ("Fermented milk products",),
    ),
    DairyProduct(
        "uht_milk",
        "UHT Milk",
        "040120",
        ("uht milk", "uht"),
        ("Milk - Excluding Butter",),
    ),
    DairyProduct(
        "paneer",
        "Paneer",
        "040610",
        ("paneer",),
        ("Cheese",),
    ),
)

PRODUCT_BY_CODE = {product.code: product for product in DAIRY_PRODUCTS}

FAOSTAT_MILK_ITEMS = {
    "Milk, whole fresh cow": "Cow milk",
    "Milk, whole fresh buffalo": "Buffalo milk",
    "Milk, whole fresh goat": "Goat milk",
    "Milk, whole fresh sheep": "Sheep milk",
}

FAOSTAT_PRODUCTION_URL = (
    "https://bulks-faostat.fao.org/production/"
    "Production_LivestockPrimary_E_All_Data_(Normalized).zip"
)
FAOSTAT_FOOD_BALANCE_URL = (
    "https://bulks-faostat.fao.org/production/"
    "Food_Balance_Sheet_E_All_Data_(Normalized).zip"
)

WORLD_BANK_COUNTRIES_URL = "https://api.worldbank.org/v2/country"
WORLD_BANK_POPULATION_URL = "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL"
WORLD_BANK_GDP_URL = "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD"
WORLD_BANK_INDICATOR_URL = "https://api.worldbank.org/v2/country/all/indicator/{indicator_code}"
NASA_POWER_MONTHLY_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
UN_M49_URL = "https://unstats.un.org/SDGAPI/v1/sdg/GeoArea/List"
COMTRADE_URL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
FAOSTAT_API_BASE_URL = "https://faostatservices.fao.org/api/v1"
FAOSTAT_GUEST_TOKEN_URL = f"{FAOSTAT_API_BASE_URL}/auth/guest"
FAOSTAT_BULK_DOWNLOADS_URL = f"{FAOSTAT_API_BASE_URL}/en/bulkdownloads"
FAOSTAT_PRODUCTION_DOMAIN = "QCL"
FAOSTAT_FOOD_BALANCE_DOMAIN = "FBSH"

SOURCE_DESCRIPTIONS = (
    (
        "UN Comtrade",
        "Official annual HS import and export flows, values, quantities, and partner records.",
        "Published according to each reporting economy's schedule; the pipeline checks on demand.",
    ),
    (
        "FAOSTAT",
        "Official agricultural production and Food Balance Sheet indicators for dairy supply and demand context.",
        "FAO bulk releases are checked on demand; historical observations are preserved.",
    ),
    (
        "World Bank Open Data",
        "Country metadata, coordinates, income group, region, annual population, and selected economic indicators.",
        "The pipeline checks the public API on demand.",
    ),
    (
        "NASA POWER",
        "Satellite-derived monthly climate context: 2 m temperature and corrected precipitation at country coordinates.",
        "The pipeline checks selected countries on demand; it does not infer farm-level climate conditions.",
    ),
    (
        "UN Statistics M49",
        "Official numeric geographic codes used to align World Bank countries with UN Comtrade reporters.",
        "The pipeline checks the public API on demand.",
    ),
)
