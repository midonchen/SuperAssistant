from __future__ import annotations

import uuid

from sqlalchemy import select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import KnowledgeEntryModel
from core.schemas import KnowledgeEntry, KnowledgeEntryCreateRequest, KnowledgeEntryUpdateRequest, utc_now
from core.store.base import StoreBase

THINKING_MODEL_PRESETS = [
    {"name": "多元思维模型", "category": "基础科学", "description": "用跨学科视角看问题，避免单一维度的局限", "applications": "决策、复杂分析"},
    {"name": "框架思维", "category": "其他学科", "description": "先构建事件的框架，再按模块细化内容", "applications": "写作、项目开发、计划、目标管理、学习"},
    {"name": "正向思维", "category": "心理学", "description": "方法→结果：从需求推导实现方式", "applications": "结果推导、数学证明、创造性活动"},
    {"name": "逆向思维", "category": "心理学", "description": "结果→原因→方法：从结果倒推方法与需求", "applications": "事件复盘、总结性活动"},
    {"name": "批判性思维", "category": "逻辑学", "description": "预设事件是错误的，通过证据证明它是对的", "applications": "论证、审查"},
    {"name": "归零思维", "category": "其他学科", "description": "任何时候带着学习的心态去接纳新事物", "applications": "持续学习"},
    {"name": "长线思维", "category": "其他学科", "description": "考虑问题时加上时间维度，从未来看现在的决策", "applications": "投资、人生规划"},
    {"name": "系统性思维", "category": "其他学科", "description": "从整个事情的脉络去考虑问题", "applications": "复杂问题分析"},
]

VALUE_PRINCIPLE_PRESETS = [
    {"name": "理性", "category": "价值观", "description": "确定什么是重要的，什么是最重要的"},
    {"name": "工匠精神", "category": "价值观", "description": "精益求精做好每一件事，相信做好产品就能赢得客户"},
    {"name": "个人成长放首位", "category": "价值观", "description": "打铁还需自身硬，把注意力放在自己的成长上"},
    {"name": "注意力>时间>金钱", "category": "重要概念", "description": "个人最宝贵的财富是注意力"},
    {"name": "知识的定义", "category": "重要概念", "description": "能指导更好决策、长期带来更好结果的信息；信息不等于知识"},
    {"name": "成长与成长率", "category": "重要概念", "description": "成长：每天比昨天进步一点；成长率：进步速度本身也在加速"},
    {"name": "赚钱的本质", "category": "方法论", "description": "价值：信息差、价差、稀缺性且有需求"},
    {"name": "严于律己宽以待人", "category": "原则", "description": "己所不欲勿施于人，己所欲也勿施于人"},
]


class KnowledgeStoreMixin(StoreBase):
    def _entry(self, row: KnowledgeEntryModel) -> KnowledgeEntry:
        return KnowledgeEntry(
            entry_id=row.id,
            kind=row.kind,
            name=row.name,
            category=row.category,
            description=row.description,
            applications=row.applications,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _seed_presets(self, db, user_id: str, kind: str) -> None:
        presets = THINKING_MODEL_PRESETS if kind == "thinking_model" else VALUE_PRINCIPLE_PRESETS
        for p in presets:
            db.add(
                KnowledgeEntryModel(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    kind=kind,
                    name=p["name"],
                    category=p.get("category"),
                    description=p["description"],
                    applications=p.get("applications"),
                )
            )

    def create_entry(self, user_id: str, request: KnowledgeEntryCreateRequest) -> KnowledgeEntry:
        if request.kind not in {"thinking_model", "value_principle"}:
            raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid entry kind")
        with SessionLocal() as db:
            row = KnowledgeEntryModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                kind=request.kind,
                name=request.name,
                category=request.category,
                description=request.description,
                applications=request.applications,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._entry(row)

    def list_entries(self, user_id: str, kind: str | None = None) -> list[KnowledgeEntry]:
        with SessionLocal() as db:
            stmt = select(KnowledgeEntryModel).where(KnowledgeEntryModel.user_id == user_id)
            if kind:
                stmt = stmt.where(KnowledgeEntryModel.kind == kind)
            rows = db.scalars(stmt.order_by(KnowledgeEntryModel.created_at.asc())).all()
            if not rows and kind:
                self._seed_presets(db, user_id, kind)
                db.commit()
                rows = db.scalars(stmt.order_by(KnowledgeEntryModel.created_at.asc())).all()
            return [self._entry(r) for r in rows]

    def update_entry(self, user_id: str, entry_id: str, request: KnowledgeEntryUpdateRequest) -> KnowledgeEntry:
        with SessionLocal() as db:
            row = db.scalar(
                select(KnowledgeEntryModel).where(
                    KnowledgeEntryModel.id == entry_id, KnowledgeEntryModel.user_id == user_id
                )
            )
            if row is None:
                raise KeyError("knowledge entry not found")
            if request.name is not None:
                row.name = request.name
            if request.category is not None:
                row.category = request.category
            if request.description is not None:
                row.description = request.description
            if request.applications is not None:
                row.applications = request.applications
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._entry(row)

    def delete_entry(self, user_id: str, entry_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(KnowledgeEntryModel).where(
                    KnowledgeEntryModel.id == entry_id, KnowledgeEntryModel.user_id == user_id
                )
            )
            if row is None:
                raise KeyError("knowledge entry not found")
            db.delete(row)
            db.commit()
