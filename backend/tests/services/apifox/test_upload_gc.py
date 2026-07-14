"""Binary 上传文件孤儿 GC · 移除/替换后清理未引用行（评审遗留收尾）。

被测：upload_service.purge_unreferenced_uploads —— 扫接口/用例/场景 http 步骤的
binary body file_id，删本项目不再被引用的上传文件。
"""

import json
from datetime import timedelta

from app.models.apifox.case import ApifoxEndpointCase
from app.models.apifox.endpoint import ApifoxEndpoint
from app.models.apifox.scenario import ApifoxScenario, ApifoxScenarioStep
from app.repositories.apifox import upload_repo
from app.services.apifox import upload_service as svc


def _upload(db, pid=1, name="f"):
    return svc.create_upload(db, pid, name, "application/octet-stream", b"x")


def _binary_spec(fid):
    return json.dumps({"body": {"type": "binary", "file_id": fid}})


def test_purge_removes_orphan_keeps_endpoint_referenced(db):
    referenced = _upload(db, name="ref")
    orphan = _upload(db, name="orphan")
    db.add(ApifoxEndpoint(project_id=1, name="ep", method="POST", path="/x",
                          request_spec=_binary_spec(referenced.id)))
    db.commit()

    removed = svc.purge_unreferenced_uploads(db, 1, grace=timedelta(0))

    assert removed == 1
    assert upload_repo.get_file(db, referenced.id) is not None
    assert upload_repo.get_file(db, orphan.id) is None


def test_purge_keeps_file_referenced_by_case(db):
    ref = _upload(db, name="ref")
    db.add(ApifoxEndpointCase(project_id=1, endpoint_id=1, name="c", request_spec=_binary_spec(ref.id)))
    db.commit()

    assert svc.purge_unreferenced_uploads(db, 1, grace=timedelta(0)) == 0
    assert upload_repo.get_file(db, ref.id) is not None


def test_purge_keeps_file_referenced_by_scenario_http_step(db):
    ref = _upload(db, name="ref")
    scenario = ApifoxScenario(project_id=1, name="s")
    db.add(scenario)
    db.commit()
    db.add(ApifoxScenarioStep(scenario_id=scenario.id, type="http",
                              config=json.dumps({"request_spec": {"body": {"type": "binary", "file_id": ref.id}}})))
    db.commit()

    assert svc.purge_unreferenced_uploads(db, 1, grace=timedelta(0)) == 0
    assert upload_repo.get_file(db, ref.id) is not None


def test_purge_removes_when_body_no_longer_binary(db):
    # 移除文件后 body 变 none：该上传成孤儿被清（模拟 clearFile 后保存）
    orphan = _upload(db, name="orphan")
    db.add(ApifoxEndpoint(project_id=1, name="ep", method="POST", path="/x",
                          request_spec=json.dumps({"body": {"type": "none"}})))
    db.commit()

    assert svc.purge_unreferenced_uploads(db, 1, grace=timedelta(0)) == 1
    assert upload_repo.get_file(db, orphan.id) is None


def test_grace_period_protects_recent_uploads(db):
    # 刚上传未保存的在途文件（默认 1h 宽限内）不被并发保存的 GC 误删
    fresh = _upload(db, name="in-flight")

    removed = svc.purge_unreferenced_uploads(db, 1)  # 默认宽限期

    assert removed == 0
    assert upload_repo.get_file(db, fresh.id) is not None


def test_purge_is_project_scoped(db):
    orphan_p1 = _upload(db, pid=1, name="a")
    other_p2 = _upload(db, pid=2, name="b")

    svc.purge_unreferenced_uploads(db, 1, grace=timedelta(0))

    assert upload_repo.get_file(db, orphan_p1.id) is None
    assert upload_repo.get_file(db, other_p2.id) is not None  # 跨项目不动
