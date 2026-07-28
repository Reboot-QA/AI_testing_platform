"""用例有序处理器（前/后置自由混排）· 持久化往返。

阶段1：仅存取往返（引擎按序执行在后续阶段）。空列表存 None → 运行时回退旧固定管线。
"""

from app.routers.apifox.case_schemas import CaseCreate, CaseUpdate
from app.routers.apifox.schemas import ProcessorRow
from app.services.apifox import case_service as svc


def test_processors_roundtrip_on_create(db, make_endpoint):
    ep = make_endpoint()

    out = svc.create_case(
        db,
        project_id=1,
        endpoint_id=ep.id,
        data=CaseCreate(
            name="P",
            post_processors=[
                ProcessorRow(kind="wait", wait_ms=500),
                ProcessorRow(kind="assertion", type="status_code", operator="eq", expected="200"),
            ],
        ),
    )

    assert [p.kind for p in out.post_processors] == ["wait", "assertion"]
    assert out.post_processors[0].wait_ms == 500
    assert out.post_processors[1].expected == "200"
    assert out.pre_processors == []  # 未传 → 空 → 回退旧管线


def test_processors_update_and_clear(db, make_case):
    case = make_case()

    svc.update_case(db, case, CaseUpdate(pre_processors=[ProcessorRow(kind="script", script_id=1)]))
    assert case.pre_processors is not None

    # 清空 → 存 None（回退旧管线）
    svc.update_case(db, case, CaseUpdate(pre_processors=[]))
    assert case.pre_processors is None
