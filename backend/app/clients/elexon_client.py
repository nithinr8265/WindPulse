"""HTTP client module for retrieving datasets from the Elexon BMRS API."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.config import Settings, get_settings
from app.models.schemas import WindActualRecord, WindForecastRecord

logger = logging.getLogger(__name__)


class ElexonAPIError(Exception):
    """Custom exception raised when an error occurs while communicating with the Elexon API."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ElexonClient:
    """Asynchronous client for querying Elexon BMRS dataset streams."""

    def __init__(self, settings: Optional[Settings] = None, client: Optional[httpx.AsyncClient] = None):
        self.settings = settings or get_settings()
        self.base_url = self.settings.ELEXON_BASE_URL.rstrip("/")
        self.timeout = self.settings.HTTP_TIMEOUT_SECONDS
        self._external_client = client
        # In-memory cache for API responses: key -> (timestamp, data)
        self._cache: Dict[str, Any] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        """Return an active httpx.AsyncClient instance."""
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(timeout=self.timeout)

    async def fetch_actual_wind_generation(
        self,
        from_date: str = "2026-01-01",
        to_date: str = "2026-01-31",
        use_cache: bool = True,
    ) -> List[WindActualRecord]:
        """Fetch actual half-hourly wind generation records from FUELHH dataset.

        Parameters:
            from_date: Start settlement date / UTC start date (YYYY-MM-DD).
            to_date: End settlement date / UTC end date (YYYY-MM-DD).
            use_cache: Whether to use cached data if available.

        Returns:
            List of validated WindActualRecord instances filtered to fuelType='WIND'
            and strictly contained within the UTC calendar window [target_start, target_end).
        """
        cache_key = f"FUELHH:{from_date}:{to_date}"
        if use_cache and cache_key in self._cache:
            logger.debug("Returning cached FUELHH actuals for %s to %s", from_date, to_date)
            return self._cache[cache_key]

        start_dt = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)
        target_start = start_dt
        target_end = end_dt + timedelta(days=1)

        # In Great Britain electricity markets:
        # - During BST (UTC+1), the settlement day starts at 23:00 UTC on D-1 and ends at 23:00 UTC on D.
        # - The final hour of the UTC calendar day (23:00 and 23:30 UTC on to_date) falls into
        #   settlementDate = to_date + 1 in UK local time (SP 1 and SP 2).
        # - To ensure complete coverage of the requested UTC window [target_start, target_end),
        #   the upstream settlement-date query must extend to to_date + 1 day.
        settlement_date_to = (end_dt + timedelta(days=1)).strftime("%Y-%m-%d")

        endpoint = f"{self.base_url}/datasets/FUELHH/stream"
        params = {
            "settlementDateFrom": from_date,
            "settlementDateTo": settlement_date_to,
        }

        logger.info(
            "Fetching actuals from Elexon FUELHH: %s params=%s target_window=[%s, %s)",
            endpoint,
            params,
            target_start.isoformat(),
            target_end.isoformat(),
        )
        client = await self._get_client()
        should_close = self._external_client is None

        try:
            response = await client.get(
                endpoint,
                params=params,
                headers={"Accept": "application/json", "User-Agent": "WindPulse-Wind-Evaluation/1.0"},
            )
            if response.status_code != 200:
                logger.error("Elexon FUELHH returned HTTP %s: %s", response.status_code, response.text[:200])
                raise ElexonAPIError(
                    f"Elexon FUELHH API returned error status {response.status_code}",
                    status_code=response.status_code,
                )

            raw_records = response.json()
            if not isinstance(raw_records, list):
                logger.error("Unexpected FUELHH response structure: expected list, got %s", type(raw_records))
                raise ElexonAPIError("Malformed response structure from Elexon FUELHH stream")

            records_by_time: Dict[datetime, WindActualRecord] = {}
            for item in raw_records:
                # Filter strictly for fuelType == 'WIND'
                if item.get("fuelType") != "WIND":
                    continue

                # Ensure required fields exist and are valid
                start_time_str = item.get("startTime")
                generation_val = item.get("generation")
                if not start_time_str or generation_val is None:
                    continue

                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))

                    # Strict UTC timestamp filter: [target_start, target_end)
                    # where target_end is midnight immediately following the requested final UTC date
                    if not (target_start <= start_time < target_end):
                        continue

                    record = WindActualRecord(
                        startTime=start_time,
                        generation=float(generation_val),
                        fuelType="WIND",
                        settlementDate=item.get("settlementDate"),
                        settlementPeriod=item.get("settlementPeriod"),
                    )
                    records_by_time[start_time] = record
                except (ValueError, TypeError) as parse_err:
                    logger.warning("Skipping invalid actual record %s: %s", item, parse_err)
                    continue

            # Sort deterministically by startTime
            wind_records = sorted(records_by_time.values(), key=lambda r: r.startTime)
            logger.info("Retrieved and filtered %d actual wind records", len(wind_records))

            if use_cache:
                self._cache[cache_key] = wind_records

            return wind_records

        except httpx.TimeoutException as exc:
            logger.error("Timeout connecting to Elexon FUELHH stream: %s", exc)
            raise ElexonAPIError("Request to Elexon FUELHH stream timed out") from exc
        except httpx.RequestError as exc:
            logger.error("Network error connecting to Elexon FUELHH stream: %s", exc)
            raise ElexonAPIError(f"Network error querying Elexon FUELHH: {str(exc)}") from exc
        finally:
            if should_close:
                await client.aclose()

    async def fetch_wind_forecasts(
        self,
        from_date: str = "2026-01-01",
        to_date: str = "2026-01-31",
        use_cache: bool = True,
    ) -> List[WindForecastRecord]:
        """Fetch wind forecasts from WINDFOR dataset for target settlement dates.

        For day-ahead evaluation of delivery dates `from_date` to `to_date`, forecasts
        must have been published in the window leading up to those delivery days.
        To capture all relevant day-ahead forecasts (e.g. published on D-1 or earlier),
        the query begins two days before `from_date` and ends on `to_date`.

        Parameters:
            from_date: Target start delivery date (YYYY-MM-DD).
            to_date: Target end delivery date (YYYY-MM-DD).
            use_cache: Whether to use cached data if available.

        Returns:
            List of validated WindForecastRecord instances whose target startTime falls
            within the target delivery window.
        """
        cache_key = f"WINDFOR:{from_date}:{to_date}"
        if use_cache and cache_key in self._cache:
            logger.debug("Returning cached WINDFOR forecasts for %s to %s", from_date, to_date)
            return self._cache[cache_key]

        endpoint = f"{self.base_url}/datasets/WINDFOR/stream"

        # Calculate publication time window:
        # Start 2 days before the start date to capture day-ahead forecasts for day 1
        start_dt = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
        pub_from_dt = start_dt - timedelta(days=2)
        end_dt = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)
        pub_to_dt = end_dt + timedelta(days=1, seconds=-1)

        # Evaluation target window boundaries
        target_start = start_dt
        target_end = end_dt + timedelta(days=1)

        params = {
            "publishDateTimeFrom": pub_from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": pub_to_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        logger.info("Fetching forecasts from Elexon WINDFOR: %s params=%s", endpoint, params)
        client = await self._get_client()
        should_close = self._external_client is None

        try:
            response = await client.get(
                endpoint,
                params=params,
                headers={"Accept": "application/json", "User-Agent": "WindPulse-Wind-Evaluation/1.0"},
            )
            if response.status_code != 200:
                logger.error("Elexon WINDFOR returned HTTP %s: %s", response.status_code, response.text[:200])
                raise ElexonAPIError(
                    f"Elexon WINDFOR API returned error status {response.status_code}",
                    status_code=response.status_code,
                )

            raw_records = response.json()
            if not isinstance(raw_records, list):
                logger.error("Unexpected WINDFOR response structure: expected list, got %s", type(raw_records))
                raise ElexonAPIError("Malformed response structure from Elexon WINDFOR stream")

            forecast_records: List[WindForecastRecord] = []
            for item in raw_records:
                start_time_str = item.get("startTime")
                publish_time_str = item.get("publishTime")
                generation_val = item.get("generation")

                if not start_time_str or not publish_time_str or generation_val is None:
                    continue

                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    publish_time = datetime.fromisoformat(publish_time_str.replace("Z", "+00:00"))

                    # Only keep forecasts targeting the requested delivery window
                    if not (target_start <= start_time < target_end):
                        continue

                    record = WindForecastRecord(
                        startTime=start_time,
                        publishTime=publish_time,
                        generation=float(generation_val),
                        dataset=item.get("dataset", "WINDFOR"),
                    )
                    forecast_records.append(record)
                except (ValueError, TypeError) as parse_err:
                    logger.warning("Skipping invalid forecast record %s: %s", item, parse_err)
                    continue

            # Sort by target startTime, then publishTime
            forecast_records.sort(key=lambda r: (r.startTime, r.publishTime))
            logger.info("Retrieved and filtered %d target forecast records", len(forecast_records))

            if use_cache:
                self._cache[cache_key] = forecast_records

            return forecast_records

        except httpx.TimeoutException as exc:
            logger.error("Timeout connecting to Elexon WINDFOR stream: %s", exc)
            raise ElexonAPIError("Request to Elexon WINDFOR stream timed out") from exc
        except httpx.RequestError as exc:
            logger.error("Network error connecting to Elexon WINDFOR stream: %s", exc)
            raise ElexonAPIError(f"Network error querying Elexon WINDFOR: {str(exc)}") from exc
        finally:
            if should_close:
                await client.aclose()
