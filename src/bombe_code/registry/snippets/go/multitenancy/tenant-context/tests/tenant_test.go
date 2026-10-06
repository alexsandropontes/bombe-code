package multitenancy
import (
	"context"
	"testing"
)
func TestTenant(t *testing.T) {
	ctx := WithTenant(context.Background(), "empresa-123")
	if TenantFromContext(ctx) != "empresa-123" {
		t.Fatal("tenant incorreto")
	}
}
