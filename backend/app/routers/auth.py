from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_admin, get_current_user, get_password_hash, verify_password
from app.database import get_db
from app.models.department import Department
from app.models.user import User
from app.schemas import ActionResultOut, Token, UserCreate, UserOut, UserPasswordChange, UserProfileUpdate
from app.services.login_lock_service import is_login_locked, record_login_failure, record_login_success
from app.services.permission_service import ensure_default_permissions, get_user_menu_keys

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserOut)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if user_in.email and db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="邮箱已存在")

    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        role=user_in.role,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    ensure_default_permissions(db, user)
    return _build_user_out(user, db)


def _build_user_out(user: User, db: Session) -> UserOut:
    department_name = user.department.name if user.department else ""
    if not department_name and user.department_id:
        department = db.query(Department).filter(Department.id == user.department_id).first()
        department_name = department.name if department else ""

    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        login_locked=user.login_locked,
        login_failed_count=user.login_failed_count,
        department_id=user.department_id,
        department_name=department_name,
        created_at=user.created_at,
        menu_permissions=get_user_menu_keys(db, user),
    )


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if user and is_login_locked(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已锁定，请联系管理员解锁",
        )
    if not user or not verify_password(form_data.password, user.hashed_password):
        record_login_failure(db, user)
        if user and is_login_locked(user):
            db.refresh(user)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="密码错误次数过多，账号已锁定，请联系管理员解锁",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    record_login_success(db, user)
    token = create_access_token(data={"sub": user.username})
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _build_user_out(current_user, db)


@router.put("/me", response_model=UserOut)
def update_me(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.email is not None:
        existing = (
            db.query(User)
            .filter(User.email == data.email, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="邮箱已存在")
        current_user.email = data.email
    if data.full_name is not None:
        current_user.full_name = data.full_name
    db.commit()
    db.refresh(current_user)
    return _build_user_out(current_user, db)


@router.post("/logout", response_model=ActionResultOut)
def logout(current_user: User = Depends(get_current_user)):
    """退出登录。JWT 无状态，服务端此处作为登出钩子/审计点；前端据此清理本地会话。"""
    return {"message": "已退出登录"}


@router.put("/password", response_model=ActionResultOut)
def change_password(
    data: UserPasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    if data.old_password == data.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    current_user.hashed_password = get_password_hash(data.new_password)
    current_user.must_change_password = False
    db.commit()
    return {"message": "密码已修改"}
