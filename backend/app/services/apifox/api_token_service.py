"""Apifox 项目级 API Token · 业务层。

生成/校验 token；「通过 API 导入/导出」端点用 resolve_token 换取 project_id。
校验命中即更新 last_used_at（单条 UPDATE，不整块读改写）。
"""

import secrets
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.api_token import ApifoxApiToken
from app.utils.time_util import now_local

_TOKEN_PREFIX = "afx_"


def generate_token() -> str:
    return _TOKEN_PREFIX + secrets.token_urlsafe(32)


def list_tokens(db: Session, project_id: int) -> List[ApifoxApiToken]:
    return (
        db.query(ApifoxApiToken)
        .filter(ApifoxApiToken.project_id == project_id, ApifoxApiToken.revoked.is_(False))
        .order_by(ApifoxApiToken.id.desc())
        .all()
    )


def create_token(db: Session, project_id: int, name: str, created_by: Optional[int]) -> ApifoxApiToken:
    token = ApifoxApiToken(
        project_id=project_id,
        name=name or "API Token",
        token=generate_token(),
        created_by=created_by,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def revoke_token(db: Session, token: ApifoxApiToken) -> None:
    token.revoked = True
    db.commit()


def resolve_token(db: Session, raw_token: str) -> Optional[ApifoxApiToken]:
    """有效 token → 记录并回其行；无效/已吊销 → None。"""
    if not raw_token:
        return None
    row = (
        db.query(ApifoxApiToken)
        .filter(ApifoxApiToken.token == raw_token.strip(), ApifoxApiToken.revoked.is_(False))
        .first()
    )
    if not row:
        return None
    db.query(ApifoxApiToken).filter(ApifoxApiToken.id == row.id).update(
        {ApifoxApiToken.last_used_at: now_local()}, synchronize_session=False
    )
    db.commit()
    return row
