from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_tenant_ctx: ContextVar[str] = ContextVar("tenant_id", default="default")

def get_current_tenant() -> str:
    return _tenant_ctx.get()

def set_current_tenant(tenant_id: str):
    _tenant_ctx.set(tenant_id)

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID") or "default"
        token = _tenant_ctx.set(tenant_id)
        request.state.tenant_id = tenant_id
        try:
            response = await call_next(request)
            return response
        finally:
            _tenant_ctx.reset(token)
