from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """
    Enterprise Standard: Two-Step Authentication Flow
    """

    @staticmethod
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        return pwd_context.hash(password)

    @staticmethod
    def authenticate_step_1_discovery(email: str, db: Session):
        """
        Step 1: Global Context Discovery
        Identifies which vault (tenant) the user belongs to.
        """
        # Rule: Explicitly query the 'admin' schema
        query = text("""
            SELECT t.tenant_slug
            FROM admin.global_users gu
            JOIN admin.tenants t ON gu.tenant_id = t.id
            WHERE gu.email = :email AND t.is_active = true
        """)

        result = db.execute(query, {"email": email}).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in any registered tenant."
            )

        return result.tenant_slug

    @staticmethod
    def authenticate_step_2_validation(email: str, password: str, tenant_slug: str, db: Session):
        """
        Step 2: Local Context Validation
        Switches context and validates password inside the Vault.
        """
        # Rule: Switch path to specific tenant schema
        schema_name = f"op_{tenant_slug}"
        db.execute(text(f"SET search_path TO {schema_name}"))

        # Rule: Local table 'users' inside the tenant schema
        # In a real scenario, use passlib/bcrypt for hash validation
        user_query = text("SELECT * FROM users WHERE email = :email AND deleted_at IS NULL")
        user = db.execute(user_query, {"email": email}).fetchone()

        if not user or not AuthService.verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials for this tenant."
            )

        return user
