from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.testcase import TestCase
from app.models.user import User


def seed_demo_data(db: Session) -> None:
    if db.query(User).first():
        return

    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("admin123"),
        full_name="管理员",
        role="admin",
    )
    db.add(admin)
    db.flush()

    project = Project(
        name="电商登录模块",
        description="用户登录、注册、找回密码相关功能测试",
        owner_id=admin.id,
    )
    db.add(project)
    db.flush()

    req = Requirement(
        project_id=project.id,
        title="用户登录功能",
        description="支持手机号/邮箱登录，含验证码校验、密码错误锁定、记住登录状态。",
        req_type="functional",
        priority="P0",
        status="approved",
        created_by_id=admin.id,
    )
    db.add(req)
    db.flush()

    db.add(
        TestCase(
            project_id=project.id,
            requirement_id=req.id,
            title="验证正确账号密码登录成功",
            case_type="functional",
            priority="P0",
            preconditions="用户已注册且账号状态正常",
            steps="1. 打开登录页\n2. 输入正确账号和密码\n3. 点击登录",
            expected_results="登录成功，跳转至首页，显示用户信息",
            tags="登录,冒烟",
            source="manual",
            review_status="approved",
            created_by_id=admin.id,
        )
    )
    db.commit()
