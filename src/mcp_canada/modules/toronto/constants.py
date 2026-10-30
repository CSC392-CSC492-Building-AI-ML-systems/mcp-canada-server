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
# Toronto republishes files under new resource ids.
NEIGHBOURHOOD_PROFILES_DATASET_ID = "neighbourhood-profiles"
NEIGHBOURHOOD_PROFILE_YEARS: dict[int, dict[str, str]] = {
    2006: {"resource_name": "neighbourhood-profiles-2006-140-model", "label_column": "Attribute"},
    2011: {"resource_name": "neighbourhood-profiles-2011-140-model", "label_column": "Attribute"},
    2016: {"resource_name": "neighbourhood-profiles-2016-140-model", "label_column": "Characteristic"},
}
DEFAULT_PROFILE_YEAR = 2016
# Only 2016 has a "Neighbourhood Number" row; 2006 and 2011 share its 140 names.
PROFILE_NUMBERS_YEAR = 2016
# Rows per datastore_search page when reading a whole profile table
PROFILE_PAGE_SIZE = 1000

# 311 Service Requests — annual ZIP+CSV files, one resource per year
SERVICE_REQUESTS_DATASET_ID = "311-service-requests-customer-initiated"

# RentSafeTO — apartment building evaluation scores
RENTSAFE_EVAL_RESOURCE_ID = "244f7a02-da5c-425b-b55f-fbdd133dd732"

# Short-Term Rentals — operator registration registry
SHORT_TERM_RENTALS_RESOURCE_ID = "f4659cc1-8985-4e4a-a702-ae24352271e0"
