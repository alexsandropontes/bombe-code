from tenant import get_current_tenant, set_current_tenant

def test_tenant_context():
    assert get_current_tenant() == "default"
    set_current_tenant("tenant-123")
    assert get_current_tenant() == "tenant-123"
