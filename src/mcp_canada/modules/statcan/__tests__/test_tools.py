"""Unit tests for StatCan WDS @tool functions.

TDD: RED → GREEN → REFACTOR

Tests follow pattern:
- Happy path: mock client returns (data, was_cached), verify make_response envelope
- Error 409: mock raises HTTPStatusError with 409, verify UPSTREAM_UNAVAILABLE
- Generic error: mock raises Exception, verify UPSTREAM_ERROR
- Lang passthrough: call with lang="fr", verify _meta.lang == "fr"
- Quality: verify all tools have Use for: and Keywords: in docstring
"""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from mcp_canada.shared.errors import InvalidInput

# ─── Quality tests ────────────────────────────────────────────────────────────


class TestToolDocstringQuality:
    """Verify all tools have required BM25 discovery metadata in docstrings."""

    def _get_all_tools(self):
        from mcp_canada.modules.statcan import tools
        tool_names = [
            "sc_search_cubes",
            "sc_get_cube_metadata",
            "sc_get_code_sets",
            "sc_get_series_info_by_vector",
            "sc_get_series_info_by_coord",
            "sc_get_data_by_vector",
            "sc_get_data_by_coord",
            "sc_get_data_by_date_range",
            "sc_get_bulk_vector_data",
            "sc_get_changed_series",
            "sc_get_changed_cubes",
            # SDMX tools (Plan 02)
            "sc_get_sdmx_structure",
            "sc_get_sdmx_data",
            "sc_get_sdmx_vector_data",
            "sc_fetch_vectors_to_store",
            "sc_get_toronto_rents",
        ]
        return [(name, getattr(tools, name)) for name in tool_names]

    def test_all_tools_have_use_for_line(self):
        for name, fn in self._get_all_tools():
            doc = inspect.getdoc(fn) or ""
            assert "Use for:" in doc, f"{name} missing 'Use for:' in docstring"

    def test_all_tools_have_keywords_line(self):
        for name, fn in self._get_all_tools():
            doc = inspect.getdoc(fn) or ""
            assert "Keywords:" in doc, f"{name} missing 'Keywords:' in docstring"

    def test_all_tools_have_eight_or_more_keywords(self):
        for name, fn in self._get_all_tools():
            doc = inspect.getdoc(fn) or ""
            kw_line = ""
            for line in doc.split("\n"):
                if "Keywords:" in line:
                    kw_line = line
                    break
            keywords = [k.strip() for k in kw_line.replace("Keywords:", "").split(",") if k.strip()]
            assert len(keywords) >= 8, (
                f"{name} has only {len(keywords)} keywords (need >= 8): {keywords}"
            )


# ─── Helper to make mock 409 HTTPStatusError ─────────────────────────────────


def _make_409_error() -> httpx.HTTPStatusError:
    mock_resp = MagicMock()
    mock_resp.status_code = 409
    return httpx.HTTPStatusError("maintenance", request=MagicMock(), response=mock_resp)


def _make_500_error() -> httpx.HTTPStatusError:
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    return httpx.HTTPStatusError("server error", request=MagicMock(), response=mock_resp)


# ─── sc_search_cubes ─────────────────────────────────────────────────────────


class TestScSearchCubes:

    @pytest.mark.asyncio
    async def test_returns_make_response_with_data(self):
        from mcp_canada.modules.statcan.schemas import CubeLite
        mock_cube = CubeLite(
            product_id=18100004,
            cansim_id="326-0021",
            title_en="Consumer Price Index, monthly",
            title_fr="Indice des prix",
            start_date="1914-01",
            end_date="2026-03",
            release_time="2026-03-19",
            archived=False,
            frequency_code=5,
            frequency="Monthly",
            subject_codes=["18"],
            survey_codes=["2301"],
        )
        with patch(
            "mcp_canada.modules.statcan.tools.search_cubes",
            new=AsyncMock(return_value=([mock_cube], False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_search_cubes
            result = await sc_search_cubes("consumer price")
        assert "_meta" in result
        assert result["_meta"]["source"]["api"] == "statcan-wds"
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 1
        assert result["data"][0]["product_id"] == 18100004

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.search_cubes",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_search_cubes
            result = await sc_search_cubes("consumer price")
        assert "error" in result
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"
        assert "maintenance" in result["error"]["message"].lower() or "08:30" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_generic_exception_returns_upstream_error(self):
        with patch(
            "mcp_canada.modules.statcan.tools.search_cubes",
            new=AsyncMock(side_effect=Exception("network failure")),
        ):
            from mcp_canada.modules.statcan.tools import sc_search_cubes
            result = await sc_search_cubes("consumer price")
        assert "error" in result
        assert result["error"]["code"] == "UPSTREAM_ERROR"

    @pytest.mark.asyncio
    async def test_lang_passthrough(self):
        with patch(
            "mcp_canada.modules.statcan.tools.search_cubes",
            new=AsyncMock(return_value=([], False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_search_cubes
            result = await sc_search_cubes("consumer", lang="fr")
        assert result["_meta"]["lang"] == "fr"


# ─── sc_get_cube_metadata ─────────────────────────────────────────────────────


class TestScGetCubeMetadata:

    @pytest.mark.asyncio
    async def test_returns_make_response_with_metadata(self):
        from mcp_canada.modules.statcan.schemas import CubeMetadata
        mock_meta = CubeMetadata(
            product_id=18100004,
            cansim_id="326-0021",
            title_en="Consumer Price Index, monthly",
            title_fr="Indice des prix",
            start_date="1914-01",
            end_date="2026-03",
            frequency_code=5,
            frequency="Monthly",
            nb_series=1000,
            nb_datapoints=500000,
            dimensions=[],
            footnotes=[],
        )
        with patch(
            "mcp_canada.modules.statcan.tools.get_cube_metadata",
            new=AsyncMock(return_value=(mock_meta, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_cube_metadata
            result = await sc_get_cube_metadata(18100004)
        assert "_meta" in result
        assert result["data"]["product_id"] == 18100004

    @pytest.mark.asyncio
    async def test_value_error_returns_upstream_error(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_cube_metadata",
            new=AsyncMock(side_effect=ValueError("FAILED WDS response")),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_cube_metadata
            result = await sc_get_cube_metadata(999999999)
        assert "error" in result
        assert result["error"]["code"] == "UPSTREAM_ERROR"

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_cube_metadata",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_cube_metadata
            result = await sc_get_cube_metadata(18100004)
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_lang_fr_passthrough(self):
        from mcp_canada.modules.statcan.schemas import CubeMetadata
        mock_meta = CubeMetadata(
            product_id=18100004, cansim_id="", title_en="", title_fr="",
            start_date="", end_date="", frequency_code=5, frequency="Monthly",
            nb_series=0, nb_datapoints=0, dimensions=[], footnotes=[],
        )
        with patch(
            "mcp_canada.modules.statcan.tools.get_cube_metadata",
            new=AsyncMock(return_value=(mock_meta, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_cube_metadata
            result = await sc_get_cube_metadata(18100004, lang="fr")
        assert result["_meta"]["lang"] == "fr"


# ─── sc_get_code_sets ─────────────────────────────────────────────────────────


class TestScGetCodeSets:

    @pytest.mark.asyncio
    async def test_returns_make_response_with_code_sets(self):
        from mcp_canada.modules.statcan.schemas import CodeSetEntry, CodeSets
        mock_sets = CodeSets(
            frequency=[CodeSetEntry(code=5, desc_en="Monthly", desc_fr="Mensuel")],
            scalar=[CodeSetEntry(code=0, desc_en="units", desc_fr="unités")],
            status=[CodeSetEntry(code=0, desc_en="Normal", desc_fr="Normal")],
            symbol=[],
            security_level=[],
            uom=[],
        )
        with patch(
            "mcp_canada.modules.statcan.tools.get_code_sets",
            new=AsyncMock(return_value=(mock_sets, True)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_code_sets
            result = await sc_get_code_sets()
        assert "_meta" in result
        assert result["_meta"]["cached"] is True
        assert "frequency" in result["data"]
        assert "scalar" in result["data"]

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_code_sets",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_code_sets
            result = await sc_get_code_sets()
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_code_sets",
            new=AsyncMock(side_effect=Exception("timeout")),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_code_sets
            result = await sc_get_code_sets()
        assert result["error"]["code"] == "UPSTREAM_ERROR"


# ─── sc_get_series_info_by_vector ─────────────────────────────────────────────


class TestScGetSeriesInfoByVector:

    @pytest.mark.asyncio
    async def test_returns_make_response(self):
        from mcp_canada.modules.statcan.schemas import SeriesInfo
        mock_info = SeriesInfo(
            product_id=18100004, coordinate="1.1", vector_id=32164132,
            frequency_code=5, frequency="Monthly", scalar_factor_code=0,
            scalar_factor="units", decimals=1, terminated=False,
            title_en="CPI", title_fr="IPC", uom_code=239,
        )
        with patch(
            "mcp_canada.modules.statcan.tools.get_series_info_by_vector",
            new=AsyncMock(return_value=(mock_info, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_series_info_by_vector
            result = await sc_get_series_info_by_vector(32164132)
        assert "_meta" in result
        assert result["data"]["vector_id"] == 32164132

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_series_info_by_vector",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_series_info_by_vector
            result = await sc_get_series_info_by_vector(32164132)
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_lang_fr(self):
        from mcp_canada.modules.statcan.schemas import SeriesInfo
        mock_info = SeriesInfo(
            product_id=18100004, coordinate="1.1", vector_id=32164132,
            frequency_code=5, frequency="Monthly", scalar_factor_code=0,
            scalar_factor="units", decimals=1, terminated=False,
            title_en="CPI", title_fr="IPC", uom_code=239,
        )
        with patch(
            "mcp_canada.modules.statcan.tools.get_series_info_by_vector",
            new=AsyncMock(return_value=(mock_info, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_series_info_by_vector
            result = await sc_get_series_info_by_vector(32164132, lang="fr")
        assert result["_meta"]["lang"] == "fr"


# ─── sc_get_series_info_by_coord ─────────────────────────────────────────────


class TestScGetSeriesInfoByCoord:

    @pytest.mark.asyncio
    async def test_returns_make_response(self):
        from mcp_canada.modules.statcan.schemas import SeriesInfo
        mock_info = SeriesInfo(
            product_id=35100003, coordinate="1.12.0.0.0.0.0.0.0.0", vector_id=32164132,
            frequency_code=9, frequency="Annual", scalar_factor_code=6,
            scalar_factor="hundreds", decimals=2, terminated=False,
            title_en="GDP", title_fr="PIB", uom_code=301,
        )
        with patch(
            "mcp_canada.modules.statcan.tools.get_series_info_by_coord",
            new=AsyncMock(return_value=(mock_info, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_series_info_by_coord
            result = await sc_get_series_info_by_coord(35100003, "1.12")
        assert "_meta" in result
        assert result["data"]["product_id"] == 35100003

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_series_info_by_coord",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_series_info_by_coord
            result = await sc_get_series_info_by_coord(35100003, "1.12")
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_value_error_returns_upstream_error(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_series_info_by_coord",
            new=AsyncMock(side_effect=ValueError("bad coord")),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_series_info_by_coord
            result = await sc_get_series_info_by_coord(35100003, "bad")
        assert result["error"]["code"] == "UPSTREAM_ERROR"


# ─── sc_get_data_by_vector ────────────────────────────────────────────────────


class TestScGetDataByVector:

    @pytest.mark.asyncio
    async def test_returns_observations_list(self):
        from mcp_canada.modules.statcan.schemas import ObservationRow
        mock_rows = [
            ObservationRow(
                ref_per="2026-03", ref_per_raw="2026-03", value=163.4,
                decimals=1, scalar_factor_code=0, scalar_factor="units",
                frequency_code=5, frequency="Monthly", status_code=0,
                symbol_code=0, release_time="2026-03-19 08:30",
            ),
        ]
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_vector",
            new=AsyncMock(return_value=(mock_rows, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_data_by_vector
            result = await sc_get_data_by_vector(32164132, 12)
        assert "_meta" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 1
        assert result["data"][0]["value"] == 163.4

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_vector",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_data_by_vector
            result = await sc_get_data_by_vector(32164132)
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_vector",
            new=AsyncMock(side_effect=Exception("timeout")),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_data_by_vector
            result = await sc_get_data_by_vector(32164132)
        assert result["error"]["code"] == "UPSTREAM_ERROR"

    @pytest.mark.asyncio
    async def test_lang_fr(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_vector",
            new=AsyncMock(return_value=([], False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_data_by_vector
            result = await sc_get_data_by_vector(32164132, lang="fr")
        assert result["_meta"]["lang"] == "fr"


# ─── sc_get_data_by_coord ─────────────────────────────────────────────────────


class TestScGetDataByCoord:

    @pytest.mark.asyncio
    async def test_returns_observations_list(self):
        from mcp_canada.modules.statcan.schemas import ObservationRow
        mock_rows = [
            ObservationRow(
                ref_per="2023-01", ref_per_raw="2023-01", value=99.5,
                decimals=1, scalar_factor_code=0, scalar_factor="units",
                frequency_code=9, frequency="Annual", status_code=0,
                symbol_code=0, release_time="2023-03-01 08:30",
            ),
        ]
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=AsyncMock(return_value=(mock_rows, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_data_by_coord
            result = await sc_get_data_by_coord(35100003, "1.12", 5)
        assert "_meta" in result
        assert result["data"][0]["ref_per"] == "2023-01"

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_data_by_coord
            result = await sc_get_data_by_coord(35100003, "1.12")
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_lang_fr(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=AsyncMock(return_value=([], False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_data_by_coord
            result = await sc_get_data_by_coord(35100003, "1.12", lang="fr")
        assert result["_meta"]["lang"] == "fr"


# ─── sc_get_data_by_date_range ────────────────────────────────────────────────


class TestScGetDataByDateRange:

    @pytest.mark.asyncio
    async def test_returns_observations_list(self):
        from mcp_canada.modules.statcan.schemas import ObservationRow
        mock_rows = [
            ObservationRow(
                ref_per="2023-01", ref_per_raw="2023-01", value=99.5,
                decimals=1, scalar_factor_code=0, scalar_factor="units",
                frequency_code=9, frequency="Annual", status_code=0,
                symbol_code=0, release_time="2023-03-01 08:30",
            ),
        ]
        with patch(
            "mcp_canada.modules.statcan.tools.get_data_by_ref_period",
            new=AsyncMock(return_value=(mock_rows, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_data_by_date_range
            result = await sc_get_data_by_date_range(32164132, "2020-01-01", "2023-01-01")
        assert "_meta" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 1

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_data_by_ref_period",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_data_by_date_range
            result = await sc_get_data_by_date_range(32164132, "2020-01-01", "2023-01-01")
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_lang_fr(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_data_by_ref_period",
            new=AsyncMock(return_value=([], False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_data_by_date_range
            result = await sc_get_data_by_date_range(32164132, "2020-01-01", "2023-01-01", lang="fr")
        assert result["_meta"]["lang"] == "fr"


# ─── sc_get_bulk_vector_data ──────────────────────────────────────────────────


class TestScGetBulkVectorData:

    @pytest.mark.asyncio
    async def test_returns_make_response_with_dict(self):
        from mcp_canada.modules.statcan.schemas import ObservationRow
        mock_row = ObservationRow(
            ref_per="2024-01", ref_per_raw="2024-01", value=150.2,
            decimals=1, scalar_factor_code=0, scalar_factor="units",
            frequency_code=5, frequency="Monthly", status_code=0,
            symbol_code=0, release_time="2024-02-15 08:30",
        )
        mock_data: dict[int, list] = {74804: [mock_row]}
        with patch(
            "mcp_canada.modules.statcan.tools.get_bulk_vector_data",
            new=AsyncMock(return_value=(mock_data, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_bulk_vector_data
            result = await sc_get_bulk_vector_data([74804, 32164132], "2023-01-01T08:30", "2024-01-01T08:30")
        assert "_meta" in result
        assert "74804" in result["data"] or 74804 in result["data"]

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_bulk_vector_data",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_bulk_vector_data
            result = await sc_get_bulk_vector_data([74804], "2023-01-01T08:30", "2024-01-01T08:30")
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_lang_fr(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_bulk_vector_data",
            new=AsyncMock(return_value=({}, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_bulk_vector_data
            result = await sc_get_bulk_vector_data([74804], "2023-01-01T08:30", "2024-01-01T08:30", lang="fr")
        assert result["_meta"]["lang"] == "fr"


# ─── sc_get_changed_series ────────────────────────────────────────────────────


class TestScGetChangedSeries:

    @pytest.mark.asyncio
    async def test_returns_list_of_changed_series(self):
        mock_data = [
            {"vectorId": 41690973, "productId": 18100004, "coordinate": "1.1", "releaseTime": "2026-04-07 08:30"},
            {"vectorId": 32164132, "productId": 35100003, "coordinate": "1.12", "releaseTime": "2026-04-07 08:30"},
        ]
        with patch(
            "mcp_canada.modules.statcan.tools.get_changed_series",
            new=AsyncMock(return_value=(mock_data, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_changed_series
            result = await sc_get_changed_series()
        assert "_meta" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_changed_series",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_changed_series
            result = await sc_get_changed_series()
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_lang_fr(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_changed_series",
            new=AsyncMock(return_value=([], False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_changed_series
            result = await sc_get_changed_series(lang="fr")
        assert result["_meta"]["lang"] == "fr"


# ─── sc_get_changed_cubes ─────────────────────────────────────────────────────


class TestScGetChangedCubes:

    @pytest.mark.asyncio
    async def test_returns_list_of_changed_cubes(self):
        mock_data = [
            {"productId": 18100004, "releaseTime": "2026-04-07 08:30"},
        ]
        with patch(
            "mcp_canada.modules.statcan.tools.get_changed_cubes",
            new=AsyncMock(return_value=(mock_data, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_changed_cubes
            result = await sc_get_changed_cubes("2024-01-15")
        assert "_meta" in result
        assert isinstance(result["data"], list)
        assert result["data"][0]["productId"] == 18100004

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_changed_cubes",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_changed_cubes
            result = await sc_get_changed_cubes("2024-01-15")
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_changed_cubes",
            new=AsyncMock(side_effect=Exception("timeout")),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_changed_cubes
            result = await sc_get_changed_cubes("2024-01-15")
        assert result["error"]["code"] == "UPSTREAM_ERROR"

    @pytest.mark.asyncio
    async def test_lang_fr(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_changed_cubes",
            new=AsyncMock(return_value=([], False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_changed_cubes
            result = await sc_get_changed_cubes("2024-01-15", lang="fr")
        assert result["_meta"]["lang"] == "fr"


# ─── sc_get_sdmx_structure ────────────────────────────────────────────────────


class TestScGetSdmxStructure:

    @pytest.mark.asyncio
    async def test_returns_make_response_with_dimensions(self):
        from mcp_canada.modules.statcan.schemas import SDMXCodeValue, SDMXDimension, SDMXStructure
        mock_structure = SDMXStructure(
            product_id=18100004,
            dimensions=[
                SDMXDimension(
                    position=1,
                    id="GEO",
                    codelist_id="CL_GEO_18100004",
                    codes=[SDMXCodeValue(id="1", name_en="Canada", name_fr="Canada")],
                ),
                SDMXDimension(
                    position=2,
                    id="PRODUCTS",
                    codelist_id="CL_PRODUCTS_18100004",
                    codes=[SDMXCodeValue(id="1", name_en="All-items", name_fr="Ensemble")],
                ),
            ],
            suggested_key="1.1",
        )
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_structure",
            new=AsyncMock(return_value=(mock_structure, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_structure
            result = await sc_get_sdmx_structure(18100004)
        assert "_meta" in result
        assert result["_meta"]["source"]["api"] == "statcan-sdmx"
        assert "dimensions" in result["data"]
        assert len(result["data"]["dimensions"]) == 2
        assert result["data"]["suggested_key"] == "1.1"
        dim0 = result["data"]["dimensions"][0]
        assert "position" in dim0
        assert "id" in dim0
        assert "codes" in dim0

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_structure",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_structure
            result = await sc_get_sdmx_structure(18100004)
        assert "error" in result
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_value_error_returns_invalid_input(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_structure",
            new=AsyncMock(side_effect=InvalidInput("bad product")),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_structure
            result = await sc_get_sdmx_structure(999)
        assert "error" in result
        assert result["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_generic_exception_returns_upstream_error(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_structure",
            new=AsyncMock(side_effect=Exception("network failure")),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_structure
            result = await sc_get_sdmx_structure(18100004)
        assert "error" in result
        assert result["error"]["code"] == "UPSTREAM_ERROR"

    @pytest.mark.asyncio
    async def test_lang_passthrough(self):
        from mcp_canada.modules.statcan.schemas import SDMXStructure
        mock_structure = SDMXStructure(product_id=18100004, dimensions=[], suggested_key="")
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_structure",
            new=AsyncMock(return_value=(mock_structure, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_structure
            result = await sc_get_sdmx_structure(18100004, lang="fr")
        assert result["_meta"]["lang"] == "fr"


# ─── sc_get_sdmx_data ─────────────────────────────────────────────────────────


class TestScGetSdmxData:

    def _make_obs_rows(self):
        from mcp_canada.modules.statcan.schemas import SDMXObservationRow
        return [
            SDMXObservationRow(period="2024-01", value=163.4, dimensions={"GEO": "Canada"}),
            SDMXObservationRow(period="2024-02", value=164.0, dimensions={"GEO": "Canada"}),
        ]

    @pytest.mark.asyncio
    async def test_happy_path_with_raw_key(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_data",
            new=AsyncMock(return_value=(self._make_obs_rows(), False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_data
            result = await sc_get_sdmx_data(18100004, key="1.1")
        assert "_meta" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 2
        assert result["data"][0]["period"] == "2024-01"
        assert result["data"][0]["value"] == 163.4

    @pytest.mark.asyncio
    async def test_invalid_input_last_n_with_date_range(self):
        from mcp_canada.modules.statcan.tools import sc_get_sdmx_data
        result = await sc_get_sdmx_data(18100004, key="1.1", last_n=5, start_period="2024-01")
        assert "error" in result
        assert result["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_invalid_input_last_n_with_end_period(self):
        from mcp_canada.modules.statcan.tools import sc_get_sdmx_data
        result = await sc_get_sdmx_data(18100004, key="1.1", last_n=3, end_period="2024-12")
        assert "error" in result
        assert result["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_dimensions_dict_calls_build_key(self):
        from mcp_canada.modules.statcan.schemas import SDMXCodeValue, SDMXDimension, SDMXStructure
        mock_structure = SDMXStructure(
            product_id=18100004,
            dimensions=[
                SDMXDimension(
                    position=1, id="GEO", codelist_id="CL_GEO",
                    codes=[SDMXCodeValue(id="1", name_en="Canada", name_fr="Canada")],
                ),
            ],
            suggested_key="1",
        )
        with (
            patch(
                "mcp_canada.modules.statcan.tools.get_sdmx_structure",
                new=AsyncMock(return_value=(mock_structure, False)),
            ),
            patch(
                "mcp_canada.modules.statcan.tools.get_sdmx_data",
                new=AsyncMock(return_value=(self._make_obs_rows(), False)),
            ) as mock_get_data,
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_data
            result = await sc_get_sdmx_data(18100004, dimensions={"GEO": "1"})
        assert "_meta" in result
        # Verify get_sdmx_data was called with a non-empty key built from dimensions
        mock_get_data.assert_called_once()
        called_key = mock_get_data.call_args[0][1]
        assert called_key == "1"

    @pytest.mark.asyncio
    async def test_key_wins_over_dimensions(self):
        """When both key and dimensions are provided, key takes precedence."""
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_data",
            new=AsyncMock(return_value=(self._make_obs_rows(), False)),
        ) as mock_get_data:
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_data
            result = await sc_get_sdmx_data(18100004, key="1.1", dimensions={"GEO": "2"})
        assert "_meta" in result
        # Key "1.1" used — no structure fetch needed
        mock_get_data.assert_called_once()
        called_key = mock_get_data.call_args[0][1]
        assert called_key == "1.1"

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_data",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_data
            result = await sc_get_sdmx_data(18100004, key="1.1")
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_lang_passthrough(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_data",
            new=AsyncMock(return_value=([], False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_data
            result = await sc_get_sdmx_data(18100004, key="1.1", lang="fr")
        assert result["_meta"]["lang"] == "fr"


# ─── sc_get_sdmx_vector_data ──────────────────────────────────────────────────


class TestScGetSdmxVectorData:

    def _make_obs_rows(self):
        from mcp_canada.modules.statcan.schemas import SDMXObservationRow
        return [
            SDMXObservationRow(period="2024-01", value=163.4, dimensions={}),
        ]

    @pytest.mark.asyncio
    async def test_happy_path(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_vector_data",
            new=AsyncMock(return_value=(self._make_obs_rows(), False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_vector_data
            result = await sc_get_sdmx_vector_data(41690973, start_period="2024-01", end_period="2024-12")
        assert "_meta" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 1
        assert result["data"][0]["period"] == "2024-01"
        assert result["data"][0]["value"] == 163.4

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_vector_data",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_vector_data
            result = await sc_get_sdmx_vector_data(41690973)
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_vector_data",
            new=AsyncMock(side_effect=Exception("timeout")),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_vector_data
            result = await sc_get_sdmx_vector_data(41690973)
        assert result["error"]["code"] == "UPSTREAM_ERROR"

    @pytest.mark.asyncio
    async def test_lang_passthrough(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_sdmx_vector_data",
            new=AsyncMock(return_value=([], False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_sdmx_vector_data
            result = await sc_get_sdmx_vector_data(41690973, lang="fr")
        assert result["_meta"]["lang"] == "fr"


# ─── sc_fetch_vectors_to_store ────────────────────────────────────────────────


class TestScFetchVectorsToStore:

    def _make_bulk_data(self):
        from mcp_canada.modules.statcan.schemas import ObservationRow
        row = ObservationRow(
            ref_per="2024-01", ref_per_raw="2024-01", value=150.2,
            decimals=1, scalar_factor_code=0, scalar_factor="units",
            frequency_code=5, frequency="Monthly", status_code=0,
            symbol_code=0, release_time="2024-02-15 08:30",
        )
        return {41690973: [row], 74804: [row]}

    @pytest.mark.asyncio
    async def test_happy_path_creates_table_and_inserts(self):
        with (
            patch(
                "mcp_canada.modules.statcan.tools.get_bulk_vector_data",
                new=AsyncMock(return_value=(self._make_bulk_data(), False)),
            ),
            patch(
                "mcp_canada.modules.statcan.tools.create_table",
                new=AsyncMock(return_value=(None, False)),
            ),
            patch(
                "mcp_canada.modules.statcan.tools.insert_rows",
                new=AsyncMock(return_value=(2, False)),
            ),
        ):
            from mcp_canada.modules.statcan.tools import sc_fetch_vectors_to_store
            result = await sc_fetch_vectors_to_store(
                vector_ids=[41690973, 74804],
                start_release="2024-01-01",
                end_release="2024-12-31",
                table_name="cpi_data",
            )
        assert "_meta" in result
        assert result["data"]["stored"] == 2
        assert result["data"]["table"] == "cpi_data"
        assert isinstance(result["data"]["vectors"], list)

    @pytest.mark.asyncio
    async def test_invalid_table_name_returns_invalid_input(self):
        from mcp_canada.modules.statcan.tools import sc_fetch_vectors_to_store
        result = await sc_fetch_vectors_to_store(
            vector_ids=[41690973],
            start_release="2024-01-01",
            end_release="2024-12-31",
            table_name="drop;--",
        )
        assert "error" in result
        assert result["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_table_name_starting_with_digit_is_invalid(self):
        from mcp_canada.modules.statcan.tools import sc_fetch_vectors_to_store
        result = await sc_fetch_vectors_to_store(
            vector_ids=[41690973],
            start_release="2024-01-01",
            end_release="2024-12-31",
            table_name="1invalid",
        )
        assert "error" in result
        assert result["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_not_found_on_empty_bulk_data(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_bulk_vector_data",
            new=AsyncMock(return_value=({}, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_fetch_vectors_to_store
            result = await sc_fetch_vectors_to_store(
                vector_ids=[99999999],
                start_release="2024-01-01",
                end_release="2024-12-31",
                table_name="empty_table",
            )
        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_not_found_on_all_empty_obs_lists(self):
        """Empty obs lists per vector should also yield NOT_FOUND."""
        with patch(
            "mcp_canada.modules.statcan.tools.get_bulk_vector_data",
            new=AsyncMock(return_value=({41690973: []}, False)),
        ):
            from mcp_canada.modules.statcan.tools import sc_fetch_vectors_to_store
            result = await sc_fetch_vectors_to_store(
                vector_ids=[41690973],
                start_release="2024-01-01",
                end_release="2024-12-31",
                table_name="empty_table",
            )
        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_bulk_vector_data",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_fetch_vectors_to_store
            result = await sc_fetch_vectors_to_store(
                vector_ids=[41690973],
                start_release="2024-01-01",
                end_release="2024-12-31",
                table_name="cpi_data",
            )
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_lang_passthrough(self):
        with (
            patch(
                "mcp_canada.modules.statcan.tools.get_bulk_vector_data",
                new=AsyncMock(return_value=(self._make_bulk_data(), False)),
            ),
            patch(
                "mcp_canada.modules.statcan.tools.create_table",
                new=AsyncMock(return_value=(None, False)),
            ),
            patch(
                "mcp_canada.modules.statcan.tools.insert_rows",
                new=AsyncMock(return_value=(2, False)),
            ),
        ):
            from mcp_canada.modules.statcan.tools import sc_fetch_vectors_to_store
            result = await sc_fetch_vectors_to_store(
                vector_ids=[41690973, 74804],
                start_release="2024-01-01",
                end_release="2024-12-31",
                table_name="cpi_data",
                lang="fr",
            )
        assert result["_meta"]["lang"] == "fr"


# ─── sc_get_toronto_rents ─────────────────────────────────────────────────────


def _obs(year: int, value: float | None):
    from mcp_canada.modules.statcan.schemas import ObservationRow
    return ObservationRow(
        ref_per=f"{year}-10-01", ref_per_raw=f"{year}-10-01", value=value,
        decimals=0, scalar_factor_code=0, scalar_factor="units",
        frequency_code=12, frequency="Annual", status_code=0,
        symbol_code=0, release_time="2026-01-15 08:30",
    )


# (product_id, coordinate) -> rows the fake client returns, newest first
_RENT_SERIES = {
    (34100133, "125.1.1"): [_obs(2025, 1491.0), _obs(2024, 1450.0)],
    (34100133, "125.1.2"): [_obs(2025, 1761.0), _obs(2024, 1700.0)],
    (34100133, "125.1.3"): [_obs(2025, 2046.0), _obs(2024, 1990.0)],
    (34100133, "125.1.4"): [_obs(2025, 2317.0), _obs(2024, 2250.0)],
    (34100127, "23"): [_obs(2025, 3.0), _obs(2024, 2.2)],
}


def _fake_client(series: dict, cached: bool = False):
    async def fake(product_id: int, coordinate: str, n: int = 10):
        return series.get((product_id, coordinate), [])[:n], cached
    return AsyncMock(side_effect=fake)


class TestScGetTorontoRents:

    @pytest.mark.asyncio
    async def test_merges_series_by_year_newest_first(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=_fake_client(_RENT_SERIES),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_toronto_rents
            result = await sc_get_toronto_rents()
        assert result["data"] == [
            {"year": 2025, "bachelor": 1491.0, "one_bedroom": 1761.0,
             "two_bedroom": 2046.0, "three_bedroom_plus": 2317.0,
             "vacancy_rate_pct": 3.0},
            {"year": 2024, "bachelor": 1450.0, "one_bedroom": 1700.0,
             "two_bedroom": 1990.0, "three_bedroom_plus": 2250.0,
             "vacancy_rate_pct": 2.2},
        ]

    @pytest.mark.asyncio
    async def test_calls_all_five_series_with_years_as_n(self):
        mock = _fake_client(_RENT_SERIES)
        with patch("mcp_canada.modules.statcan.tools.get_latest_n_by_coord", new=mock):
            from mcp_canada.modules.statcan.tools import sc_get_toronto_rents
            await sc_get_toronto_rents(years=3)
        calls = {(c.args[0], c.args[1], c.args[2]) for c in mock.call_args_list}
        assert calls == {(pid, coord, 3) for pid, coord in _RENT_SERIES}

    @pytest.mark.asyncio
    async def test_years_limits_rows(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=_fake_client(_RENT_SERIES),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_toronto_rents
            result = await sc_get_toronto_rents(years=1)
        assert [row["year"] for row in result["data"]] == [2025]

    @pytest.mark.asyncio
    async def test_missing_year_in_one_series_is_null(self):
        series = dict(_RENT_SERIES)
        series[(34100127, "23")] = [_obs(2025, 3.0)]          # no 2024 vacancy
        series[(34100133, "125.1.1")] = [_obs(2025, None), _obs(2024, 1450.0)]
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=_fake_client(series),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_toronto_rents
            result = await sc_get_toronto_rents()
        rows = {row["year"]: row for row in result["data"]}
        assert rows[2024]["vacancy_rate_pct"] is None
        assert rows[2024]["bachelor"] == 1450.0
        assert rows[2025]["bachelor"] is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("years", [0, -1, 31])
    async def test_years_out_of_range_is_invalid_input(self, years):
        mock = _fake_client(_RENT_SERIES)
        with patch("mcp_canada.modules.statcan.tools.get_latest_n_by_coord", new=mock):
            from mcp_canada.modules.statcan.tools import sc_get_toronto_rents
            result = await sc_get_toronto_rents(years=years)
        assert result["error"]["code"] == "INVALID_INPUT"
        mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_data_is_not_found(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=_fake_client({}),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_toronto_rents
            result = await sc_get_toronto_rents()
        assert result["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_cached_true_only_when_every_series_cached(self):
        from mcp_canada.modules.statcan.tools import sc_get_toronto_rents
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=_fake_client(_RENT_SERIES, cached=True),
        ):
            assert (await sc_get_toronto_rents())["_meta"]["cached"] is True

        calls = {"n": 0}

        async def mixed(product_id, coordinate, n=10):
            calls["n"] += 1
            return _RENT_SERIES[(product_id, coordinate)], calls["n"] != 3

        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=AsyncMock(side_effect=mixed),
        ):
            assert (await sc_get_toronto_rents())["_meta"]["cached"] is False

    @pytest.mark.asyncio
    async def test_409_returns_upstream_unavailable(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=AsyncMock(side_effect=_make_409_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_toronto_rents
            result = await sc_get_toronto_rents()
        assert result["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_500_returns_upstream_error(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=AsyncMock(side_effect=_make_500_error()),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_toronto_rents
            result = await sc_get_toronto_rents()
        assert result["error"]["code"] == "UPSTREAM_ERROR"

    @pytest.mark.asyncio
    async def test_not_found_from_client(self):
        from mcp_canada.shared.errors import NotFound
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=AsyncMock(side_effect=NotFound("no series")),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_toronto_rents
            result = await sc_get_toronto_rents()
        assert result["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_upstream_error(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_toronto_rents
            result = await sc_get_toronto_rents()
        assert result["error"]["code"] == "UPSTREAM_ERROR"
        assert "boom" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_lang_fr(self):
        with patch(
            "mcp_canada.modules.statcan.tools.get_latest_n_by_coord",
            new=_fake_client(_RENT_SERIES),
        ):
            from mcp_canada.modules.statcan.tools import sc_get_toronto_rents
            result = await sc_get_toronto_rents(lang="fr")
        assert result["_meta"]["lang"] == "fr"
