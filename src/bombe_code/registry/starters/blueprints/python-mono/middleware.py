from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

async def tenant_context_middleware(request: Request, call_next):
    """
    Enterprise Standard Middleware: Dynamic Context Switching
    Rule: Executes 'SET search_path' before every database operation.
    """
    # 1. Retrieve tenant_slug from state (populated by Auth during login)
    # or from the JWT payload in authenticated requests.
    tenant_slug = getattr(request.state, "tenant_slug", None)

    if tenant_slug:
        # 2. Get DB session from request state
        db: Session = request.state.db

        # 3. Apply physical isolation
        # Rule: Only schemas starting with 'op_' are allowed for operational data.
        schema_name = f"op_{tenant_slug}"
        try:
            db.execute(text(f"SET search_path TO {schema_name}"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid tenant context: {str(e)}")

    response = await call_next(request)
    return response
