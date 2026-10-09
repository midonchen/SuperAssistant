from __future__ import annotations

import uuid

from sqlalchemy import select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import AssetModel, InvestmentModel
from core.schemas import Asset, AssetCreateRequest, Investment, InvestmentCreateRequest
from core.store.base import StoreBase


class AssetStoreMixin(StoreBase):
    def _asset(self, row: AssetModel) -> Asset:
        return Asset(
            asset_id=row.id,
            name=row.name,
            category=row.category,
            amount=row.amount,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create_asset(self, user_id: str, request: AssetCreateRequest) -> Asset:
        if request.category not in {"cash", "stock", "fund", "property", "insurance"}:
            raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid asset category")
        with SessionLocal() as db:
            row = AssetModel(
                id=str(uuid.uuid4()), user_id=user_id, name=request.name, category=request.category, amount=request.amount
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._asset(row)

    def list_assets(self, user_id: str) -> list[Asset]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(AssetModel).where(AssetModel.user_id == user_id).order_by(AssetModel.created_at.asc())
            ).all()
            return [self._asset(r) for r in rows]

    def delete_asset(self, user_id: str, asset_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(select(AssetModel).where(AssetModel.id == asset_id, AssetModel.user_id == user_id))
            if row is None:
                raise KeyError("asset not found")
            db.delete(row)
            db.commit()


class InvestmentStoreMixin(StoreBase):
    def _investment(self, row: InvestmentModel) -> Investment:
        return Investment(
            investment_id=row.id,
            name=row.name,
            amount=row.amount,
            return_rate=row.return_rate,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create_investment(self, user_id: str, request: InvestmentCreateRequest) -> Investment:
        if request.status not in {"active", "closed"}:
            raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid investment status")
        with SessionLocal() as db:
            row = InvestmentModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=request.name,
                amount=request.amount,
                return_rate=request.return_rate,
                status=request.status,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._investment(row)

    def list_investments(self, user_id: str) -> list[Investment]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(InvestmentModel)
                .where(InvestmentModel.user_id == user_id)
                .order_by(InvestmentModel.created_at.desc())
            ).all()
            return [self._investment(r) for r in rows]

    def delete_investment(self, user_id: str, investment_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(InvestmentModel).where(InvestmentModel.id == investment_id, InvestmentModel.user_id == user_id)
            )
            if row is None:
                raise KeyError("investment not found")
            db.delete(row)
            db.commit()
