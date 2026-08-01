"""手工测试单分页筛选（功能测试报告）。"""

from datetime import datetime

from app.models.project import Project
from app.models.test_execution import ManualTestRun
from app.models.user import User
from app.routers.test_execution import list_runs_page


def test_list_runs_page_status_filter(db):
    user = User(username="rep-u", hashed_password="x", role="tester")
    db.add(user)
    db.commit()
    project = Project(name="rep-p", owner_id=user.id)
    db.add(project)
    db.commit()

    finished = ManualTestRun(
        project_id=project.id,
        name="已完成单",
        status="finished",
        finished_at=datetime.utcnow(),
    )
    waiting = ManualTestRun(project_id=project.id, name="待开始单", status="waiting")
    db.add_all([finished, waiting])
    db.commit()

    out = list_runs_page(
        project_id=project.id,
        page=1,
        page_size=20,
        status="finished",
        keyword=None,
        date_from=None,
        date_to=None,
        db=db,
        current_user=user,
    )
    assert out.total == 1
    assert out.items[0].name == "已完成单"


def test_list_runs_page_keyword_filter(db):
    user = User(username="rep-u2", hashed_password="x", role="tester")
    db.add(user)
    db.commit()
    project = Project(name="rep-p2", owner_id=user.id)
    db.add(project)
    db.commit()

    db.add(
        ManualTestRun(
            project_id=project.id,
            name="回归测试 v1",
            status="finished",
            finished_at=datetime.utcnow(),
        )
    )
    db.add(ManualTestRun(project_id=project.id, name="其他", status="waiting"))
    db.commit()

    out = list_runs_page(
        project_id=project.id,
        page=1,
        page_size=20,
        status=None,
        keyword="回归",
        date_from=None,
        date_to=None,
        db=db,
        current_user=user,
    )
    assert out.total == 1
    assert "回归" in out.items[0].name
