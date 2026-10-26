"""Integration tests querying live Elexon BMRS API to verify UTC boundary filtering
and period reconciliation across GMT, BST, and DST transitions.
"""

import os
from datetime import datetime, timezone
import pytest

from app.clients.elexon_client import ElexonClient
from app.services.forecast_service import ForecastService

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_ELEXON_TESTS") != "1",
    reason="Live Elexon API tests are opt-in; set RUN_LIVE_ELEXON_TESTS=1 to run them.",
)

@pytest.mark.asyncio
class TestLiveElexonReconciliation:
    """Live verification tests against Elexon BMRS API streams."""

    async def test_live_october_25_autumn_dst_reconciliation(self):
        """Verifies that 25 October 2026 (UK autumn DST clock change) yields exactly 48 actuals,
        strictly excludes 24 October records, achieves 100% coverage, and reconciles perfectly:
        24 matched + 24 unmatched half-hourly = 48 actual records.
        """
        client = ElexonClient()
        service = ForecastService()

        actuals = await client.fetch_actual_wind_generation("2026-10-25", "2026-10-25", use_cache=False)
        forecasts = await client.fetch_wind_forecasts("2026-10-25", "2026-10-25", use_cache=False)

        # 1. Total actual records retrieved for the UTC day must be exactly 48 (not 50!)
        assert len(actuals) == 48

        # 2. Verify all 48 records fall strictly inside [2026-10-25 00:00:00Z, 2026-10-26 00:00:00Z)
        utc_start = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)
        utc_end = datetime(2026, 10, 26, 0, 0, tzinfo=timezone.utc)
        for act in actuals:
            assert utc_start <= act.startTime < utc_end, f"Record leaked: {act.startTime}"
            # Ensure no records from 24 October leak in
            assert act.startTime.day == 25

        # 3. Exactly 24 records at :00 and 24 at :30
        at_00 = [a for a in actuals if a.startTime.minute == 0]
        at_30 = [a for a in actuals if a.startTime.minute == 30]
        assert len(at_00) == 24
        assert len(at_30) == 24

        # 4. Evaluation reconciliation
        res = service.evaluate(
            actuals=actuals,
            forecasts=forecasts,
            from_date="2026-10-25",
            to_date="2026-10-25",
        )

        s = res.summary
        assert s.totalExpectedHourlyPeriods == 24
        assert s.totalActualHalfHourlyPeriods == 48
        assert s.eligibleForecastsCount == 24
        assert s.matchedCount == 24
        assert s.missingHourlyForecastCount == 0
        assert s.missingHourlyActualCount == 0
        assert s.unmatchedHalfHourlyActualsCount == 24
        assert s.coveragePercentage == 100.0
        assert s.actualRecordsCount == 48

        # Invariant: 24 matched + 24 unmatched :30 == 48 actuals retrieved
        assert s.matchedCount + s.unmatchedHalfHourlyActualsCount == s.actualRecordsCount == 48

    async def test_live_october_24_normal_bst_reconciliation(self):
        """Verifies that 24 October 2026 (a normal BST day) captures the full 48 half-hours
        in UTC, including 23:00 and 23:30 UTC from settlement date 2026-10-25.
        """
        client = ElexonClient()
        service = ForecastService()

        actuals = await client.fetch_actual_wind_generation("2026-10-24", "2026-10-24", use_cache=False)
        forecasts = await client.fetch_wind_forecasts("2026-10-24", "2026-10-24", use_cache=False)

        assert len(actuals) == 48
        res = service.evaluate(actuals, forecasts, "2026-10-24", "2026-10-24")

        s = res.summary
        assert s.totalExpectedHourlyPeriods == 24
        assert s.matchedCount == 24
        assert s.unmatchedHalfHourlyActualsCount == 24
        assert s.actualRecordsCount == 48
        assert s.coveragePercentage == 100.0
        assert s.matchedCount + s.unmatchedHalfHourlyActualsCount == s.actualRecordsCount == 48
