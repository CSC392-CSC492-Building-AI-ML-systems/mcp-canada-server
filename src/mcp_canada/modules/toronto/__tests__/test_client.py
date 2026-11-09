"""Unit tests for Toronto Open Data client module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_canada.modules.toronto.__tests__.conftest import (
    SAMPLE_311_PACKAGE_SHOW,
    SAMPLE_DATASTORE_RESPONSE,
    SAMPLE_DATASET_COUNT_RESPONSE,
    SAMPLE_ORGANIZATION_LIST_RESPONSE,
    SAMPLE_PACKAGE_SEARCH_RESPONSE,
    SAMPLE_PACKAGE_SHOW_RESPONSE,
    SAMPLE_RENTSAFE_RECORDS,
    SAMPLE_RESOURCE_SHOW_RESPONSE,
    SAMPLE_STR_DATASTORE_RESPONSE,
    GTFS_STOPS_ZIP_BYTES,
    GTFS_ROUTES_ZIP_BYTES,
    SERVICE_311_ZIP_BYTES,
    make_mock_response,
    make_mock_bytes_response,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_fake_cached_fetch(data: Any, was_cached: bool = False):
    """Return an async fake_cached_fetch that bypasses cache and calls fetcher."""
    async def fake_cached_fetch(key: str, ttl: int, fetcher: Any) -> tuple[Any, bool]:
        result = await fetcher()
        return result, was_cached
    return fake_cached_fetch


def _make_mock_limiter():
    """Return a mock rate limiter whose acquire() is a no-op coroutine."""
    limiter = MagicMock()
    limiter.acquire = AsyncMock()
    return limiter


# ---------------------------------------------------------------------------
# TestFetchSearchDatasets
# ---------------------------------------------------------------------------


class TestFetchSearchDatasets:
    @pytest.mark.asyncio
    async def test_returns_shaped_dataset_summaries(self) -> None:
        """fetch_search_datasets returns list of shaped dicts with title and notes."""
        from mcp_canada.modules.toronto.client import fetch_search_datasets

        mock_response = make_mock_response(SAMPLE_PACKAGE_SEARCH_RESPONSE)
        mock_limiter = _make_mock_limiter()

        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            results, was_cached = await fetch_search_datasets("transit")

        assert isinstance(results, list)
        assert len(results) >= 1
        assert "title" in results[0]
        assert "id" in results[0]
        assert was_cached is False

    @pytest.mark.asyncio
    async def test_resources_count_field_present(self) -> None:
        """fetch_search_datasets result dicts include num_resources."""
        from mcp_canada.modules.toronto.client import fetch_search_datasets

        mock_response = make_mock_response(SAMPLE_PACKAGE_SEARCH_RESPONSE)
        mock_limiter = _make_mock_limiter()

        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            results, _ = await fetch_search_datasets("transit")

        assert "num_resources" in results[0]


# ---------------------------------------------------------------------------
# TestFetchDatasetDetails
# ---------------------------------------------------------------------------


class TestFetchDatasetDetails:
    @pytest.mark.asyncio
    async def test_returns_shaped_dataset(self) -> None:
        """fetch_dataset_details returns shaped dataset dict."""
        from mcp_canada.modules.toronto.client import fetch_dataset_details

        mock_response = make_mock_response(SAMPLE_PACKAGE_SHOW_RESPONSE)
        mock_limiter = _make_mock_limiter()

        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            result, was_cached = await fetch_dataset_details("ttc-bus-delay-data")

        assert result["id"] == "ttc-bus-delay-data"
        assert "title" in result
        assert was_cached is False

    @pytest.mark.asyncio
    async def test_raises_on_404(self) -> None:
        """fetch_dataset_details raises HTTPStatusError on 404."""
        from mcp_canada.modules.toronto.client import fetch_dataset_details

        mock_limiter = _make_mock_limiter()

        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=MagicMock(), response=MagicMock()
            )
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await fetch_dataset_details("nonexistent-dataset")


# ---------------------------------------------------------------------------
# TestFetchResource
# ---------------------------------------------------------------------------


class TestFetchResource:
    @pytest.mark.asyncio
    async def test_returns_resource_dict(self) -> None:
        """fetch_resource returns shaped resource dict by ID."""
        from mcp_canada.modules.toronto.client import fetch_resource

        mock_response = make_mock_response(SAMPLE_RESOURCE_SHOW_RESPONSE)
        mock_limiter = _make_mock_limiter()

        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            result, was_cached = await fetch_resource("res-001")

        assert result["id"] == "res-001"
        assert "url" in result
        assert "datastore_active" in result


# ---------------------------------------------------------------------------
# TestFetchOrganizations
# ---------------------------------------------------------------------------


class TestFetchOrganizations:
    @pytest.mark.asyncio
    async def test_returns_list_of_orgs(self) -> None:
        """fetch_organizations returns list of org dicts with name, title, package_count."""
        from mcp_canada.modules.toronto.client import fetch_organizations

        mock_response = make_mock_response(SAMPLE_ORGANIZATION_LIST_RESPONSE)
        mock_limiter = _make_mock_limiter()

        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            results, _ = await fetch_organizations()

        assert isinstance(results, list)
        assert len(results) >= 1
        org = results[0]
        assert "name" in org
        assert "title" in org
        assert "package_count" in org


# ---------------------------------------------------------------------------
# TestFetchDatasetCount
# ---------------------------------------------------------------------------


class TestFetchDatasetCount:
    @pytest.mark.asyncio
    async def test_returns_integer_count(self) -> None:
        """fetch_dataset_count returns int total package count."""
        from mcp_canada.modules.toronto.client import fetch_dataset_count

        mock_response = make_mock_response(SAMPLE_DATASET_COUNT_RESPONSE)
        mock_limiter = _make_mock_limiter()

        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            count, _ = await fetch_dataset_count()

        assert count == 500


# ---------------------------------------------------------------------------
# TestFetchGTFSFile
# ---------------------------------------------------------------------------


class TestFetchGTFSFile:
    @pytest.mark.asyncio
    async def test_fetches_stops_txt_from_zip(self) -> None:
        """fetch_gtfs_file downloads ZIP and extracts stops.txt as list[dict]."""
        from mcp_canada.modules.toronto.client import fetch_gtfs_file

        mock_bytes_response = make_mock_bytes_response(GTFS_STOPS_ZIP_BYTES)
        mock_limiter = _make_mock_limiter()

        # The fetcher resolves the ZIP url from CKAN package_show before
        # downloading, so that call is mocked alongside the download itself.
        fake_package = (
            {"resources": [{"format": "ZIP", "url": "https://example/ttc.zip"}]},
            False,
        )
        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("mcp_canada.modules.toronto.client._api_get",
                  new=AsyncMock(return_value=fake_package)),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_bytes_response)
            mock_cls.return_value = mock_client

            results, was_cached = await fetch_gtfs_file("stops.txt")

        assert isinstance(results, list)
        assert len(results) == 3
        assert "stop_id" in results[0]
        assert "stop_name" in results[0]
        assert was_cached is False

    @pytest.mark.asyncio
    async def test_fetches_routes_txt_from_zip(self) -> None:
        """fetch_gtfs_file downloads ZIP and extracts routes.txt as list[dict]."""
        from mcp_canada.modules.toronto.client import fetch_gtfs_file

        mock_bytes_response = make_mock_bytes_response(GTFS_ROUTES_ZIP_BYTES)
        mock_limiter = _make_mock_limiter()

        # The fetcher resolves the ZIP url from CKAN package_show before
        # downloading, so that call is mocked alongside the download itself.
        fake_package = (
            {"resources": [{"format": "ZIP", "url": "https://example/ttc.zip"}]},
            False,
        )
        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("mcp_canada.modules.toronto.client._api_get",
                  new=AsyncMock(return_value=fake_package)),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_bytes_response)
            mock_cls.return_value = mock_client

            results, was_cached = await fetch_gtfs_file("routes.txt")

        assert isinstance(results, list)
        assert len(results) == 3
        assert "route_id" in results[0]
        assert "route_short_name" in results[0]


# ---------------------------------------------------------------------------
# TestFetchGTFSStops
# ---------------------------------------------------------------------------


class TestFetchGTFSStops:
    @pytest.mark.asyncio
    async def test_returns_all_stops_without_filter(self) -> None:
        """fetch_gtfs_stops without query returns all stops."""
        from mcp_canada.modules.toronto.client import fetch_gtfs_stops

        with patch(
            "mcp_canada.modules.toronto.client.fetch_gtfs_file",
            new_callable=AsyncMock,
            return_value=(
                [
                    {"stop_id": "1001", "stop_name": "Union Station", "stop_lat": "43.64", "stop_lon": "-79.38"},
                    {"stop_id": "1002", "stop_name": "Bloor-Yonge", "stop_lat": "43.67", "stop_lon": "-79.38"},
                ],
                False,
            ),
        ):
            results, _ = await fetch_gtfs_stops()

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_filters_stops_by_name_substring(self) -> None:
        """fetch_gtfs_stops with query filters stops by stop_name substring."""
        from mcp_canada.modules.toronto.client import fetch_gtfs_stops

        with patch(
            "mcp_canada.modules.toronto.client.fetch_gtfs_file",
            new_callable=AsyncMock,
            return_value=(
                [
                    {"stop_id": "1001", "stop_name": "Union Station", "stop_lat": "43.64", "stop_lon": "-79.38"},
                    {"stop_id": "1002", "stop_name": "Bloor-Yonge", "stop_lat": "43.67", "stop_lon": "-79.38"},
                ],
                False,
            ),
        ):
            results, _ = await fetch_gtfs_stops(query="Union")

        assert len(results) == 1
        assert results[0]["stop_name"] == "Union Station"


# ---------------------------------------------------------------------------
# TestFetchGTFSRoutes
# ---------------------------------------------------------------------------


class TestFetchGTFSRoutes:
    @pytest.mark.asyncio
    async def test_returns_all_routes_without_filter(self) -> None:
        """fetch_gtfs_routes without filter returns all routes."""
        from mcp_canada.modules.toronto.client import fetch_gtfs_routes

        with patch(
            "mcp_canada.modules.toronto.client.fetch_gtfs_file",
            new_callable=AsyncMock,
            return_value=(
                [
                    {"route_id": "1", "route_short_name": "1", "route_long_name": "Yonge", "route_type": "1"},
                    {"route_id": "301", "route_short_name": "301", "route_long_name": "Airport Express", "route_type": "2"},
                ],
                False,
            ),
        ):
            results, _ = await fetch_gtfs_routes()

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_filters_routes_by_type(self) -> None:
        """fetch_gtfs_routes with route_type filters client-side."""
        from mcp_canada.modules.toronto.client import fetch_gtfs_routes

        with patch(
            "mcp_canada.modules.toronto.client.fetch_gtfs_file",
            new_callable=AsyncMock,
            return_value=(
                [
                    {"route_id": "1", "route_short_name": "1", "route_long_name": "Yonge", "route_type": "1"},
                    {"route_id": "301", "route_short_name": "301", "route_long_name": "Airport Express", "route_type": "2"},
                ],
                False,
            ),
        ):
            results, _ = await fetch_gtfs_routes(route_type="2")

        assert len(results) == 1
        assert results[0]["route_id"] == "301"


# ---------------------------------------------------------------------------
# TestFetchDatastoreRecords
# ---------------------------------------------------------------------------


class TestFetchDatastoreRecords:
    @pytest.mark.asyncio
    async def test_returns_records_list(self) -> None:
        """fetch_datastore_records returns list of records from datastore_search."""
        from mcp_canada.modules.toronto.client import fetch_datastore_records

        mock_response = make_mock_response(SAMPLE_DATASTORE_RESPONSE)
        mock_limiter = _make_mock_limiter()

        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            records, was_cached = await fetch_datastore_records(
                resource_id="7f8eee5e-85fb-415c-aef3-c3bd4998445f",
                limit=10,
            )

        assert isinstance(records, list)
        assert len(records) == 2
        assert "_id" in records[0]
        assert was_cached is False

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_list(self) -> None:
        """fetch_datastore_records returns empty list when no records returned."""
        from mcp_canada.modules.toronto.client import fetch_datastore_records

        empty_response = {"success": True, "result": {"records": [], "total": 0}}
        mock_response = make_mock_response(empty_response)
        mock_limiter = _make_mock_limiter()

        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            records, _ = await fetch_datastore_records(resource_id="nonexistent-id")

        assert records == []


# ---------------------------------------------------------------------------
# TestFetchNeighbourhoodProfile
# ---------------------------------------------------------------------------


# Small stand-ins for the City's profile tables: 2016 labels rows with
# "Characteristic" and has a "Neighbourhood Number" row; 2006/2011 use "Attribute".
_PROFILE_2016 = [
    {"_id": 1, "Category": "Neighbourhood Information", "Topic": "Neighbourhood Information",
     "Data Source": "City of Toronto", "Characteristic": "Neighbourhood Number",
     "City of Toronto": None, "Annex": "95", "Rosedale-Moore Park": "98",
     "Moss Park": "73"},
    {"_id": 2, "Category": "Population", "Topic": "Population and dwellings",
     "Data Source": "Census Profile 98-316-X2016001", "Characteristic": "Population, 2016",
     "City of Toronto": "2,731,571", "Annex": "30,526", "Rosedale-Moore Park": "20,923",
     "Moss Park": "20,506"},
    {"_id": 3, "Category": "Income", "Topic": "Income of households in 2015",
     "Data Source": "Census Profile 98-316-X2016001",
     "Characteristic": "      Median total income of households in 2015 ($)",
     "City of Toronto": "65,829", "Annex": None, "Rosedale-Moore Park": None,
     "Moss Park": None},
]
_PROFILE_2011 = [
    {"_id": 1, "Category": "Population", "Topic": "Population and dwellings",
     "Attribute": "Population, 2011", "City of Toronto": "2,615,060", "Annex": "29,177",
     "Rosedale-Moore Park": "20,631", "Moss Park": "14,873"},
]


def _fake_profile_table(year: int) -> tuple[list[dict[str, Any]], bool]:
    return ({2016: _PROFILE_2016, 2011: _PROFILE_2011}[year], True)


class TestFetchProfileTable:
    @pytest.mark.asyncio
    async def test_reads_pages_until_short_page(self) -> None:
        """fetch_profile_table keeps reading until a page is shorter than the page size."""
        from mcp_canada.modules.toronto.client import fetch_profile_table

        pages = [([{"_id": 1}, {"_id": 2}], True), ([{"_id": 3}], True)]
        with (
            patch("mcp_canada.modules.toronto.client.PROFILE_PAGE_SIZE", 2),
            patch(
                "mcp_canada.modules.toronto.client._resolve_profile_resource",
                new=AsyncMock(return_value={"id": "res-2016"}),
            ),
            patch(
                "mcp_canada.modules.toronto.client.fetch_datastore_records",
                new=AsyncMock(side_effect=pages),
            ) as mock_fetch,
        ):
            rows, was_cached = await fetch_profile_table(2016)

        assert [r["_id"] for r in rows] == [1, 2, 3]
        assert was_cached is True
        assert [c.kwargs["offset"] for c in mock_fetch.call_args_list] == [0, 2]
        assert all("q" not in c.kwargs for c in mock_fetch.call_args_list)

    @pytest.mark.asyncio
    async def test_rejects_unknown_year(self) -> None:
        """fetch_profile_table raises InvalidInput for a year without a table."""
        from mcp_canada.modules.toronto.client import fetch_profile_table
        from mcp_canada.shared.errors import InvalidInput

        with pytest.raises(InvalidInput):
            await fetch_profile_table(2001)

    @pytest.mark.asyncio
    async def test_empty_table_raises(self) -> None:
        """fetch_profile_table raises UpstreamData when the table has no rows."""
        from mcp_canada.modules.toronto.client import fetch_profile_table
        from mcp_canada.shared.errors import UpstreamData

        with (
            patch(
                "mcp_canada.modules.toronto.client._resolve_profile_resource",
                new=AsyncMock(return_value={"id": "res-2016"}),
            ),
            patch(
                "mcp_canada.modules.toronto.client.fetch_datastore_records",
                new=AsyncMock(return_value=([], False)),
            ),
            pytest.raises(UpstreamData),
        ):
            await fetch_profile_table(2016)

    @pytest.mark.asyncio
    async def test_resolves_resource_by_name(self) -> None:
        """_resolve_profile_resource picks the datastore resource with the year's name."""
        from mcp_canada.modules.toronto.client import _resolve_profile_resource

        package = {
            "resources": [
                {"id": "csv-2011", "name": "neighbourhood-profiles-2011-140-model",
                 "datastore_active": False},
                {"id": "ds-2011", "name": "neighbourhood-profiles-2011-140-model",
                 "datastore_active": "True"},
            ]
        }
        with patch(
            "mcp_canada.modules.toronto.client._api_get",
            new=AsyncMock(return_value=(package, False)),
        ):
            resource = await _resolve_profile_resource(2011)
        assert resource["id"] == "ds-2011"

    @pytest.mark.asyncio
    async def test_resolves_sheet_year_by_url(self) -> None:
        """A sheet year (2021) needs a download url, not a datastore table."""
        from mcp_canada.modules.toronto.client import _resolve_profile_resource

        package = {
            "resources": [
                {"id": "x-2021", "name": "neighbourhood-profiles-2021-158-model",
                 "url": "https://example.test/2021.xlsx", "datastore_active": False},
            ]
        }
        with patch(
            "mcp_canada.modules.toronto.client._api_get",
            new=AsyncMock(return_value=(package, False)),
        ):
            resource = await _resolve_profile_resource(2021)
        assert resource["url"] == "https://example.test/2021.xlsx"

    @pytest.mark.asyncio
    async def test_missing_resource_raises(self) -> None:
        """_resolve_profile_resource raises UpstreamData when no resource matches."""
        from mcp_canada.modules.toronto.client import _resolve_profile_resource
        from mcp_canada.shared.errors import UpstreamData

        with (
            patch(
                "mcp_canada.modules.toronto.client._api_get",
                new=AsyncMock(return_value=({"resources": []}, False)),
            ),
            pytest.raises(UpstreamData),
        ):
            await _resolve_profile_resource(2016)


def _profile_2021_xlsx() -> bytes:
    """A small stand-in for the City's 2021 profile workbook."""
    import io

    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "hd2021_census_profile"
    ws.append(["Neighbourhood Name", "West Humber-Clairville", "Annex", "Yonge-Bay Corridor"])
    ws.append(["Neighbourhood Number", 1, 95, 170])
    ws.append(["TSNS 2020 Designation", "NIA", "Not an NIA or Emerging Neighbourhood",
               "Not an NIA or Emerging Neighbourhood"])
    ws.append([None, None, None, None])
    ws.append(["Total - Age groups of the population - 25% sample data", 33300, 31195, 12645])
    ws.append(["  0 to 14 years", 4295, 2390, 655])
    ws.append(["Total - Age groups of men - 25% sample data", 16500, 14900, 6200])
    ws.append(["  0 to 14 years", 2200, 1210, 330])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


class TestFetchProfileSheet:
    @pytest.mark.asyncio
    async def test_downloads_and_parses_2021(self) -> None:
        """2021 is read from its XLSX sheet with neighbourhood names kept as written."""
        from mcp_canada.modules.toronto.client import fetch_profile_table

        with (
            patch(
                "mcp_canada.modules.toronto.client.cached_fetch",
                side_effect=_make_fake_cached_fetch(None),
            ),
            patch(
                "mcp_canada.modules.toronto.client._resolve_profile_resource",
                new=AsyncMock(return_value={"url": "https://example.test/2021.xlsx"}),
            ),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=make_mock_bytes_response(_profile_2021_xlsx()))
            mock_cls.return_value = mock_client

            rows, was_cached = await fetch_profile_table(2021)

        assert was_cached is False
        assert [r["Neighbourhood Name"] for r in rows] == [
            "Neighbourhood Number",
            "TSNS 2020 Designation",
            "Total - Age groups of the population - 25% sample data",
            "  0 to 14 years",
            "Total - Age groups of men - 25% sample data",
            "  0 to 14 years",
        ]
        # Repeated labels are told apart by the unindented row above them.
        assert [r["Topic"] for r in rows[2:]] == [
            "Total - Age groups of the population - 25% sample data",
            "Total - Age groups of the population - 25% sample data",
            "Total - Age groups of men - 25% sample data",
            "Total - Age groups of men - 25% sample data",
        ]
        assert rows[3]["Yonge-Bay Corridor"] == 655
        assert list(rows[3])[:3] == ["Neighbourhood Name", "Topic", "West Humber-Clairville"]
        mock_client.get.assert_called_once_with(
            "https://example.test/2021.xlsx", follow_redirects=True
        )

    @pytest.mark.asyncio
    async def test_empty_sheet_raises(self) -> None:
        """A 2021 sheet with no rows raises UpstreamData."""
        from mcp_canada.modules.toronto.client import fetch_profile_table
        from mcp_canada.shared.errors import UpstreamData

        with (
            patch(
                "mcp_canada.modules.toronto.client._fetch_profile_sheet",
                new=AsyncMock(return_value=([], False)),
            ),
            pytest.raises(UpstreamData),
        ):
            await fetch_profile_table(2021)

    def test_parse_empty_workbook(self) -> None:
        """A sheet without any rows parses to an empty list."""
        import io

        import openpyxl

        from mcp_canada.modules.toronto.client import _parse_profile_sheet

        wb = openpyxl.Workbook()
        ws = wb.active
        assert ws is not None
        ws.title = "hd2021_census_profile"
        buffer = io.BytesIO()
        wb.save(buffer)

        assert _parse_profile_sheet(buffer.getvalue(), "hd2021_census_profile", "Label") == []


class TestFetchNeighbourhoodProfile:
    @pytest.fixture(autouse=True)
    def _tables(self):
        with patch(
            "mcp_canada.modules.toronto.client.fetch_profile_table",
            new=AsyncMock(side_effect=_fake_profile_table),
        ) as mock_table:
            yield mock_table

    @pytest.mark.asyncio
    async def test_population_matches(self) -> None:
        """Regression: "population" finds "Population, 2016" (CKAN q returned 0 rows)."""
        from mcp_canada.modules.toronto.client import fetch_neighbourhood_profile

        rows, was_cached = await fetch_neighbourhood_profile(characteristic="population")

        assert [r["Characteristic"] for r in rows] == ["Population, 2016"]
        assert rows[0]["year"] == 2016
        assert rows[0]["Annex"] == "30,526"
        assert "_id" not in rows[0]
        assert was_cached is True

    @pytest.mark.asyncio
    async def test_words_match_in_any_order(self) -> None:
        """Every word must appear, in any order, ignoring case and punctuation."""
        from mcp_canada.modules.toronto.client import fetch_neighbourhood_profile

        rows, _ = await fetch_neighbourhood_profile(characteristic="household income median")
        assert [r["Characteristic"] for r in rows] == [
            "Median total income of households in 2015 ($)"
        ]

        rows, _ = await fetch_neighbourhood_profile(characteristic="population rent")
        assert rows == []

    @pytest.mark.asyncio
    async def test_neighbourhood_filter_keeps_one_column(self) -> None:
        """A neighbourhood keeps only its own column next to the city-wide value."""
        from mcp_canada.modules.toronto.client import fetch_neighbourhood_profile

        rows, _ = await fetch_neighbourhood_profile(
            neighbourhood="rosedale", characteristic="population"
        )

        assert rows == [
            {
                "year": 2016,
                "Category": "Population",
                "Topic": "Population and dwellings",
                "Data Source": "Census Profile 98-316-X2016001",
                "Characteristic": "Population, 2016",
                "City of Toronto": "2,731,571",
                "Rosedale-Moore Park": "20,923",
            }
        ]

    @pytest.mark.asyncio
    async def test_older_year_uses_attribute_and_2016_numbers(self) -> None:
        """2011 rows are labelled Attribute; numbers are borrowed from 2016."""
        from mcp_canada.modules.toronto.client import fetch_neighbourhood_profile

        rows, _ = await fetch_neighbourhood_profile(neighbourhood="95", year=2011)

        assert rows == [
            {
                "year": 2011,
                "Category": "Population",
                "Topic": "Population and dwellings",
                "Characteristic": "Population, 2011",
                "City of Toronto": "2,615,060",
                "Annex": "29,177",
            }
        ]

    @pytest.mark.asyncio
    async def test_2021_uses_its_own_numbers(self) -> None:
        """2021 resolves numbers from its own Neighbourhood Number row, not 2016's."""
        from mcp_canada.modules.toronto.client import (
            _parse_profile_sheet,
            fetch_neighbourhood_profile,
        )

        table_2021 = _parse_profile_sheet(
            _profile_2021_xlsx(), "hd2021_census_profile", "Neighbourhood Name"
        )
        tables = {2016: _PROFILE_2016, 2021: table_2021}
        with patch(
            "mcp_canada.modules.toronto.client.fetch_profile_table",
            new=AsyncMock(side_effect=lambda year: (tables[year], True)),
        ) as mock_table:
            rows, _ = await fetch_neighbourhood_profile(
                neighbourhood="170", characteristic="total age groups population", year=2021
            )

        assert rows == [
            {
                "year": 2021,
                "Characteristic": "Total - Age groups of the population - 25% sample data",
                "Topic": "Total - Age groups of the population - 25% sample data",
                "Yonge-Bay Corridor": 12645,
            }
        ]
        assert [c.args[0] for c in mock_table.call_args_list] == [2021]

    @pytest.mark.asyncio
    async def test_limit_caps_rows(self) -> None:
        """limit caps the number of characteristic rows returned."""
        from mcp_canada.modules.toronto.client import fetch_neighbourhood_profile

        rows, _ = await fetch_neighbourhood_profile(limit=2)
        assert len(rows) == 2

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", ["Nowhere", "park", "  "])
    async def test_bad_neighbourhood_raises(self, name: str) -> None:
        """Unknown, ambiguous ("park") and blank names raise InvalidInput."""
        from mcp_canada.modules.toronto.client import fetch_neighbourhood_profile
        from mcp_canada.shared.errors import InvalidInput

        with pytest.raises(InvalidInput):
            await fetch_neighbourhood_profile(neighbourhood=name)

    @pytest.mark.asyncio
    async def test_numbers_missing_falls_back_to_names(self) -> None:
        """Without a Neighbourhood Number row, names still resolve."""
        from mcp_canada.modules.toronto.client import fetch_neighbourhood_profile

        with patch(
            "mcp_canada.modules.toronto.client.fetch_profile_table",
            new=AsyncMock(return_value=(_PROFILE_2016[1:], False)),
        ):
            rows, was_cached = await fetch_neighbourhood_profile(
                neighbourhood="Moss Park", characteristic="population"
            )

        assert rows[0]["Moss Park"] == "20,506"
        assert was_cached is False


class TestFetchNeighbourhoodComparison:
    @pytest.mark.asyncio
    async def test_returns_all_neighbourhoods(self) -> None:
        """Comparison rows hold every neighbourhood's value for the characteristic."""
        from mcp_canada.modules.toronto.client import fetch_neighbourhood_comparison

        with patch(
            "mcp_canada.modules.toronto.client.fetch_profile_table",
            new=AsyncMock(side_effect=_fake_profile_table),
        ):
            rows, _ = await fetch_neighbourhood_comparison("Population, 2016")

        assert len(rows) == 1
        assert rows[0]["Annex"] == "30,526"
        assert rows[0]["Moss Park"] == "20,506"

    @pytest.mark.asyncio
    async def test_empty_characteristic_raises(self) -> None:
        """A blank characteristic raises InvalidInput instead of returning everything."""
        from mcp_canada.modules.toronto.client import fetch_neighbourhood_comparison
        from mcp_canada.shared.errors import InvalidInput

        with pytest.raises(InvalidInput):
            await fetch_neighbourhood_comparison(" , ")


# ---------------------------------------------------------------------------
# TestFetch311Requests
# ---------------------------------------------------------------------------


class TestFetch311Requests:
    @pytest.mark.asyncio
    async def test_fetches_and_parses_311_csv(self) -> None:
        """fetch_311_requests discovers ZIP URL, downloads, parses CSV rows."""
        from mcp_canada.modules.toronto.client import fetch_311_requests

        # Package show returns dataset with year-based ZIP resource
        mock_pkg_response = make_mock_response(SAMPLE_311_PACKAGE_SHOW)
        mock_zip_response = make_mock_bytes_response(SERVICE_311_ZIP_BYTES)
        mock_limiter = _make_mock_limiter()

        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            # First call: package_show, second call: ZIP download
            mock_client.get = AsyncMock(side_effect=[mock_pkg_response, mock_zip_response])
            mock_cls.return_value = mock_client

            results, was_cached = await fetch_311_requests(year=2023)

        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_filters_by_ward(self) -> None:
        """fetch_311_requests with ward filter returns only matching rows."""
        from mcp_canada.modules.toronto.client import fetch_311_requests

        mock_pkg_response = make_mock_response(SAMPLE_311_PACKAGE_SHOW)
        mock_zip_response = make_mock_bytes_response(SERVICE_311_ZIP_BYTES)
        mock_limiter = _make_mock_limiter()

        with (
            patch("mcp_canada.modules.toronto.client.cached_fetch",
                  side_effect=_make_fake_cached_fetch(None)),
            patch("mcp_canada.modules.toronto.client.get_limiter", return_value=mock_limiter),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(side_effect=[mock_pkg_response, mock_zip_response])
            mock_cls.return_value = mock_client

            results, _ = await fetch_311_requests(year=2023, ward="Ward 1")

        # SERVICE_311_CSV_ROWS has 2 rows with "Ward 1"
        for r in results:
            assert "Ward 1" in str(r.get("ward", r))


# ---------------------------------------------------------------------------
# TestFetchRentsafeEvaluations
# ---------------------------------------------------------------------------


class TestFetchRentsafeEvaluations:
    @pytest.mark.asyncio
    async def test_returns_evaluations_list(self) -> None:
        """fetch_rentsafe_evaluations returns RentSafeTO records."""
        from mcp_canada.modules.toronto.client import fetch_rentsafe_evaluations

        with patch(
            "mcp_canada.modules.toronto.client.fetch_datastore_records",
            new_callable=AsyncMock,
            return_value=(SAMPLE_RENTSAFE_RECORDS, False),
        ):
            results, was_cached = await fetch_rentsafe_evaluations()

        assert isinstance(results, list)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_min_score_filter_applied_client_side(self) -> None:
        """fetch_rentsafe_evaluations with min_score filters records client-side."""
        from mcp_canada.modules.toronto.client import fetch_rentsafe_evaluations

        with patch(
            "mcp_canada.modules.toronto.client.fetch_datastore_records",
            new_callable=AsyncMock,
            return_value=(SAMPLE_RENTSAFE_RECORDS, False),
        ):
            # SAMPLE_RENTSAFE_RECORDS has scores "85" and "72"
            # min_score=80 should return only the "85" record
            results, _ = await fetch_rentsafe_evaluations(min_score=80)

        assert len(results) == 1
        assert int(results[0]["SCORE"]) >= 80


# ---------------------------------------------------------------------------
# TestFetchShortTermRentals
# ---------------------------------------------------------------------------


class TestFetchShortTermRentals:
    @pytest.mark.asyncio
    async def test_returns_str_records(self) -> None:
        """fetch_short_term_rentals returns STR records."""
        from mcp_canada.modules.toronto.client import fetch_short_term_rentals

        with patch(
            "mcp_canada.modules.toronto.client.fetch_datastore_records",
            new_callable=AsyncMock,
            return_value=(SAMPLE_STR_DATASTORE_RESPONSE["result"]["records"], False),
        ):
            results, was_cached = await fetch_short_term_rentals()

        assert isinstance(results, list)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_status_filter_applied_client_side(self) -> None:
        """fetch_short_term_rentals with status filter returns only matching records."""
        from mcp_canada.modules.toronto.client import fetch_short_term_rentals

        with patch(
            "mcp_canada.modules.toronto.client.fetch_datastore_records",
            new_callable=AsyncMock,
            return_value=(SAMPLE_STR_DATASTORE_RESPONSE["result"]["records"], False),
        ):
            results, _ = await fetch_short_term_rentals(status="Active")

        assert len(results) == 1
        assert results[0]["status"] == "Active"


class TestGtfsUrlIsResolvedFromCkan:
    """The GTFS zip URL must be discovered, not hardcoded.

    Regression cover for the Phase 20.1 defect. constants.GTFS_ZIP_URL pinned a
    dataset id, resource id and filename:

        .../7795b45e-...-c5b0dc4b531e/resource/f17e0649-.../download/
            ttc-routes-and-schedules.zip

    Toronto Open Data has since republished the feed under a different resource
    id and filename (opendata_ttc_schedules.zip), so the pinned URL returns 404
    and both toronto_get_ttc_stops and toronto_get_ttc_routes have been dead —
    reported as "UPSTREAM_ERROR: Failed to fetch TTC GTFS stop data", which read
    like a transient outage.

    Verified live 2026-07-25: the pinned URL 404s; the CKAN package_show
    resource URL returns a 35 MB zip. Resolving through CKAN means the next
    republish does not break the tools.
    """

    @pytest.mark.asyncio
    async def test_resolves_zip_url_from_package_show(self):
        from mcp_canada.modules.toronto import client as tc

        package = {
            "resources": [
                {"format": "ZIP", "name": "TTC Routes and Schedules Data",
                 "url": "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
                        "7795b45e-e65a-4465-81fc-c36b9dfff169/resource/"
                        "cfb6b2b8-6191-41e3-bda1-b175c51148cb/download/"
                        "opendata_ttc_schedules.zip"},
            ]
        }
        resolved = await tc._resolve_gtfs_zip_url(package)
        assert resolved.endswith("opendata_ttc_schedules.zip"), (
            f"must take the ZIP resource URL from CKAN, got {resolved}"
        )

    @pytest.mark.asyncio
    async def test_raises_when_no_zip_resource(self):
        from mcp_canada.modules.toronto import client as tc

        with pytest.raises(ValueError) as exc:
            await tc._resolve_gtfs_zip_url({"resources": [{"format": "CSV", "url": "x"}]})
        assert "zip" in str(exc.value).lower()

    def test_constants_no_longer_pin_a_download_url(self):
        """A hardcoded download URL is what rotted — it must not come back."""
        from mcp_canada.modules.toronto import constants

        assert not hasattr(constants, "GTFS_ZIP_URL"), (
            "GTFS_ZIP_URL pinned a resource id that Toronto has since changed. "
            "Resolve the URL from CKAN package_show instead."
        )
