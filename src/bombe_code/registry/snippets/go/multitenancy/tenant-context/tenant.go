package multitenancy

import "context"

type tenantKeyType struct{}
var tenantKey = tenantKeyType{}

func WithTenant(ctx context.Context, tenantID string) context.Context {
	if tenantID == "" {
		tenantID = "default"
	}
	return context.WithValue(ctx, tenantKey, tenantID)
}

func TenantFromContext(ctx context.Context) string {
	if val, ok := ctx.Value(tenantKey).(string); ok && val != "" {
		return val
	}
	return "default"
}
