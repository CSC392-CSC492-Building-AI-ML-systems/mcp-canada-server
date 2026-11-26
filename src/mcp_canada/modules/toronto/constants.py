"""Constants for the Toronto Open Data module."""

# Base URL for the Toronto CKAN API (action API v3)
BASE_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/"

# Rate limiting — conservative; Toronto's portal is not published but can be slow
RATE_GROUP = "toronto"
RATE_LIMIT = 5.0  # requests per second

# Cache TTLs in seconds
CACHE_TTL_SEARCH = 3600    # 1 hour for search results and dataset details
CACHE_TTL_META = 86400     # 24 hours for org lists (rarely change)
CACHE_TTL_DATA = 86400     # 24 hours for parsed data
CACHE_TTL_GTFS = 21600     # 6 hours for GTFS data (updated less frequently)

# Token-saving response shaping limits
MAX_DESCRIPTION_CHARS = 500
MAX_RESOURCES = 10

# ---------------------------------------------------------------------------
# Curated dataset / resource IDs
# ---------------------------------------------------------------------------

# TTC GTFS — static schedule feed
# Use the CKAN SLUG, not a uuid. Toronto republishes the GTFS feed under fresh
# dataset AND resource uuids; the slug is what stays put. The previous uuid
# (7795b45e-...-c5b0dc4b531e) now 404s on package_show.
GTFS_DATASET_ID = "ttc-routes-and-schedules"
# NOTE: do NOT pin the download URL here. A previous GTFS_ZIP_URL constant
# embedded a resource id and filename that Toronto later changed, which 404'd
# and killed both TTC tools behind an UPSTREAM_ERROR. The ZIP resource is
# resolved at call time from CKAN package_show — see
# toronto/client.py:_resolve_gtfs_zip_url.

# Neighbourhood Profiles by census year. Like the GTFS feed, each year's file
# is found by resource NAME in package_show at call time, never a pinned id:
# Toronto republishes files under new resource ids. 2006-2016 are datastore
# tables on the 140-neighbourhood model; 2021 is only an XLSX file on the
# 158-neighbourhood model, read from the named sheet.
NEIGHBOURHOOD_PROFILES_DATASET_ID = "neighbourhood-profiles"
NEIGHBOURHOOD_PROFILE_YEARS: dict[int, dict[str, str]] = {
    2001: {"resource_name": "neighbourhood-profiles-2001-140-model", "label_column": "Attribute"},
    2006: {"resource_name": "neighbourhood-profiles-2006-140-model", "label_column": "Attribute"},
    2011: {"resource_name": "neighbourhood-profiles-2011-140-model", "label_column": "Attribute"},
    2016: {"resource_name": "neighbourhood-profiles-2016-140-model", "label_column": "Characteristic"},
    2021: {
        "resource_name": "neighbourhood-profiles-2021-158-model",
        "label_column": "Neighbourhood Name",
        "sheet": "hd2021_census_profile",
    },
}
DEFAULT_PROFILE_YEAR = 2016
# 2001, 2006 and 2011 have no "Neighbourhood Number" row; they share 2016's 140 names,
# so their numbers come from 2016. 2016 and 2021 carry their own numbers.
PROFILE_NUMBERS_YEAR = 2016
# Rows per datastore_search page when reading a whole profile table
PROFILE_PAGE_SIZE = 1000

# 311 Service Requests — annual ZIP+CSV files, one resource per year
SERVICE_REQUESTS_DATASET_ID = "311-service-requests-customer-initiated"

# RentSafeTO — apartment building evaluation scores
RENTSAFE_EVAL_RESOURCE_ID = "244f7a02-da5c-425b-b55f-fbdd133dd732"

# Short-Term Rentals — operator registration registry
SHORT_TERM_RENTALS_RESOURCE_ID = "f4659cc1-8985-4e4a-a702-ae24352271e0"

# Toronto Police Service — Neighbourhood Crime Rates (ArcGIS FeatureServer, 158
# neighbourhood model, one row per neighbourhood). Field names come from the
# live layer (?f=json); the ArcGIS Hub's cached field list for this dataset is
# stale and lists fields that no longer exist.
CRIME_RATES_SERVICE_URL = (
    "https://services.arcgis.com/S9th0jAJ7bqgIRjw/arcgis/rest/services/"
    "Neighbourhood_Crime_Rates_Open_Data/FeatureServer"
)
CRIME_RATES_LAYER_ID = 0
# 158 neighbourhoods fit in one page; the cap is only a guard
CRIME_RATES_MAX_RECORDS = 500
# Tool-facing crime type -> layer field prefix (<PREFIX>_<YYYY>, <PREFIX>_RATE_<YYYY>)
CRIME_TYPES: dict[str, str] = {
    "assault": "ASSAULT",
    "auto_theft": "AUTOTHEFT",
    "bike_theft": "BIKETHEFT",
    "break_and_enter": "BREAKENTER",
    "homicide": "HOMICIDE",
    "robbery": "ROBBERY",
    "shooting": "SHOOTING",
    "theft_from_vehicle": "THEFTFROMMV",
    "theft_over": "THEFTOVER",
}
CRIME_YEARS: tuple[int, ...] = tuple(range(2014, 2026))
