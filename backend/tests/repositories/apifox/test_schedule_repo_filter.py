"""定时任务列表筛选。"""

from app.models.apifox.schedule import ApifoxSchedule
from app.repositories.apifox import schedule_repo


def _schedule(db, project_id: int, name: str) -> ApifoxSchedule:
    task = ApifoxSchedule(
        project_id=project_id,
        name=name,
        target_type="scenario",
        target_id=1,
        schedule_type="daily",
        run_time="09:00",
        enabled=True,
    )
    db.add(task)
    db.flush()
    return task


def test_list_schedules_filters_by_id_and_keyword(db):
    hit = _schedule(db, 1, "定时执行")
    _schedule(db, 1, "其它任务")
    db.commit()

    assert [t.id for t in schedule_repo.list_schedules(db, 1, schedule_id=hit.id)] == [hit.id]
    assert [t.name for t in schedule_repo.list_schedules(db, 1, keyword="执行")] == ["定时执行"]
    assert schedule_repo.list_schedules(db, 1, schedule_id=999999) == []
