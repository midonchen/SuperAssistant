from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import ActivityLogModel, ConsumptionReportModel, InventoryItemModel
from core.schemas import (
    ActionType,
    ConsumptionReport,
    MonthlyReportEntry,
    Operation,
    utc_now,
)
from core.store.base import StoreBase


def _naive_utc(dt: datetime) -> datetime:
    """SQLite may return naive datetimes; treat them as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _month_bounds(month: str) -> tuple[datetime, datetime]:
    """Return (start, end) as timezone-aware UTC datetimes for a YYYY-MM month."""
    try:
        year_s, month_s = month.split("-")
        year = int(year_s)
        month_num = int(month_s)
        if not (1 <= month_num <= 12):
            raise ValueError
        start = datetime(year, month_num, 1, tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid month; expected YYYY-MM")
    if month_num == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month_num + 1, 1, tzinfo=timezone.utc)
    return start, end


class ReportStoreMixin(StoreBase):
    def generate_monthly_report(self, household_id: str, month: str) -> ConsumptionReport:
        """Aggregate one household's monthly consumption/waste/turnover and persist a snapshot."""
        start, end = _month_bounds(month)

        consumed: dict[str, float] = {}
        wasted: dict[str, float] = {}
        with SessionLocal() as db:
            logs = db.scalars(
                select(ActivityLogModel).where(
                    ActivityLogModel.household_id == household_id,
                    ActivityLogModel.operation == Operation.SUBTRACT.value,
                )
            ).all()
            for row in logs:
                ts = _naive_utc(row.timestamp)
                if not (start <= ts < end):
                    continue
                qty = round(-(row.delta_value or 0.0), 3)
                if qty <= 0:
                    continue
                if row.action_type == ActionType.AUTO_DECAY.value:
                    wasted[row.item_key] = wasted.get(row.item_key, 0.0) + qty
                else:
                    consumed[row.item_key] = consumed.get(row.item_key, 0.0) + qty

            inventory = db.scalars(
                select(InventoryItemModel).where(InventoryItemModel.household_id == household_id)
            ).all()
            meta = {row.item_key: row for row in inventory}

            entries: list[MonthlyReportEntry] = []
            for item_key in set(consumed) | set(wasted) | set(meta):
                row = meta.get(item_key)
                turnover = None
                if row is not None and row.daily_avg_rate > 0:
                    turnover = round(row.current_stock / row.daily_avg_rate, 3)
                entries.append(
                    MonthlyReportEntry(
                        item_key=item_key,
                        item_name=row.item_name if row else item_key,
                        unit=row.unit if row else "",
                        consumed_qty=round(consumed.get(item_key, 0.0), 3),
                        wasted_qty=round(wasted.get(item_key, 0.0), 3),
                        turnover_days=turnover,
                    )
                )

            top_consumed = sorted(
                (e for e in entries if e.consumed_qty > 0),
                key=lambda e: e.consumed_qty,
                reverse=True,
            )[:10]
            wasted_list = sorted(
                (e for e in entries if e.wasted_qty > 0),
                key=lambda e: e.wasted_qty,
                reverse=True,
            )
            turnover_list = sorted(
                (e for e in entries if e.turnover_days is not None),
                key=lambda e: e.turnover_days,
            )

            suggestion = self.get_latest_suggestion(household_id)
            suggested = list(suggestion.items) if suggestion else []

            report = ConsumptionReport(
                report_id=str(uuid.uuid4()),
                household_id=household_id,
                month=month,
                generated_at=utc_now(),
                total_consumed_qty=round(sum(e.consumed_qty for e in entries), 3),
                total_wasted_qty=round(sum(e.wasted_qty for e in entries), 3),
                top_consumed=top_consumed,
                wasted=wasted_list,
                turnover=turnover_list,
                suggested_purchase=suggested,
            )

            payload = report.model_dump(mode="json")
            existing = db.scalar(
                select(ConsumptionReportModel).where(
                    ConsumptionReportModel.household_id == household_id,
                    ConsumptionReportModel.month == month,
                )
            )
            if existing is None:
                db.add(
                    ConsumptionReportModel(
                        id=str(uuid.uuid4()),
                        household_id=household_id,
                        month=month,
                        payload=payload,
                    )
                )
            else:
                existing.payload = payload
                existing.updated_at = utc_now()
            db.commit()
            return report

    def get_monthly_report(self, household_id: str, month: str) -> ConsumptionReport:
        _month_bounds(month)  # validate format
        with SessionLocal() as db:
            row = db.scalar(
                select(ConsumptionReportModel).where(
                    ConsumptionReportModel.household_id == household_id,
                    ConsumptionReportModel.month == month,
                )
            )
            if row is None:
                return self.generate_monthly_report(household_id, month)
            return ConsumptionReport.model_validate(row.payload)

    def generate_reports_for_all(self, month: str) -> dict:
        household_ids = self.list_household_ids()
        for household_id in household_ids:
            self.generate_monthly_report(household_id, month)
        return {"processed_households": len(household_ids), "month": month}
