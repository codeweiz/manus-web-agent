"""认证路由"""

import logging

from fastapi import APIRouter, Depends

from manus_web_agent.application.errors.exceptions import (
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from manus_web_agent.application.services.auth_service import AuthService
from manus_web_agent.core.toml_config import TOML_CONFIG
from manus_web_agent.domain.models.user import UserRole
from manus_web_agent.interfaces.dependencies import (
    get_auth_service,
    get_current_user,
)
from manus_web_agent.interfaces.schemas.auth import (
    AuthStatusResponse,
    ChangeFullnameRequest,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    SendVerificationCodeRequest,
    UserResponse,
)
from manus_web_agent.interfaces.schemas.base import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=APIResponse[LoginResponse])
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[LoginResponse]:
    """用户登录"""
    user, access_token, refresh_token = await auth_service.login(
        request.email, request.password
    )
    return APIResponse.success(
        LoginResponse(
            user=UserResponse.from_user(user),
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )


@router.post("/register", response_model=APIResponse[RegisterResponse])
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[RegisterResponse]:
    """用户注册"""
    user, access_token, refresh_token = await auth_service.register(
        request.fullname, request.email, request.password
    )
    return APIResponse.success(
        RegisterResponse(
            user=UserResponse.from_user(user),
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )


@router.get("/status", response_model=APIResponse[AuthStatusResponse])
async def get_auth_status() -> APIResponse[AuthStatusResponse]:
    """获取认证配置状态"""
    auth_provider = getattr(TOML_CONFIG, "auth_provider", "none")
    return APIResponse.success(
        AuthStatusResponse(
            enabled=auth_provider != "none",
            provider=auth_provider,
        )
    )


@router.post("/change-password", response_model=APIResponse[None])
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[None]:
    """修改密码"""
    await auth_service.change_password(
        current_user.get("id"), request.old_password, request.new_password
    )
    return APIResponse.success(msg="密码修改成功")


@router.post("/change-fullname", response_model=APIResponse[None])
async def change_fullname(
    request: ChangeFullnameRequest,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[None]:
    """修改姓名"""
    await auth_service.change_fullname(current_user.get("id"), request.new_fullname)
    return APIResponse.success(msg="姓名修改成功")


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[UserResponse]:
    """获取当前用户信息"""
    user = await auth_service.get_user(current_user.get("id"))
    if not user:
        raise NotFoundError("用户不存在")
    return APIResponse.success(UserResponse.from_user(user))


@router.get("/user/{user_id}", response_model=APIResponse[UserResponse])
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[UserResponse]:
    """获取指定用户信息（管理员）"""
    # 检查是否为管理员
    if current_user.get("role") != UserRole.ADMIN.value:
        raise UnauthorizedError("需要管理员权限")

    user = await auth_service.get_user(user_id)
    if not user:
        raise NotFoundError("用户不存在")
    return APIResponse.success(UserResponse.from_user(user))


@router.post("/user/{user_id}/deactivate", response_model=APIResponse[None])
async def deactivate_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[None]:
    """停用用户（管理员）"""
    if current_user.get("role") != UserRole.ADMIN.value:
        raise UnauthorizedError("需要管理员权限")

    await auth_service.deactivate_user(user_id)
    return APIResponse.success(msg="用户已停用")


@router.post("/user/{user_id}/activate", response_model=APIResponse[None])
async def activate_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[None]:
    """激活用户（管理员）"""
    if current_user.get("role") != UserRole.ADMIN.value:
        raise UnauthorizedError("需要管理员权限")

    await auth_service.activate_user(user_id)
    return APIResponse.success(msg="用户已激活")


@router.post("/refresh", response_model=APIResponse[RefreshTokenResponse])
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[RefreshTokenResponse]:
    """刷新访问令牌"""
    access_token, refresh_token = await auth_service.refresh_token(request.refresh_token)
    return APIResponse.success(
        RefreshTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )


@router.post("/logout", response_model=APIResponse[None])
async def logout(
    current_user: dict = Depends(get_current_user),
) -> APIResponse[None]:
    """用户登出"""
    # TODO: 将令牌加入黑名单
    return APIResponse.success(msg="登出成功")


@router.post("/send-verification-code", response_model=APIResponse[None])
async def send_verification_code(
    request: SendVerificationCodeRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[None]:
    """发送验证码"""
    await auth_service.send_reset_password_code(request.email)
    return APIResponse.success(msg="验证码已发送")


@router.post("/reset-password", response_model=APIResponse[None])
async def reset_password(
    request: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[None]:
    """重置密码"""
    await auth_service.reset_password(
        request.email, request.code, request.new_password
    )
    return APIResponse.success(msg="密码重置成功")
