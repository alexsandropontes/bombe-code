import pytest
from fastapi import HTTPException
from rbac import RoleChecker

def test_role_checker():
    checker = RoleChecker(["admin", "manager"])
    class DummyCred:
        role = "admin"
    assert checker(DummyCred()) is True

    class ForbiddenCred:
        role = "guest"
    with pytest.raises(HTTPException) as exc:
        checker(ForbiddenCred())
    assert exc.value.status_code == 403
