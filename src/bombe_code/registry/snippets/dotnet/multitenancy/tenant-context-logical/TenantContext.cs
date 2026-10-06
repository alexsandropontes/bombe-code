namespace CodeForge.Snippets.MultiTenancy;

using System.Threading;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;

public interface ITenantContext
{
    string? TenantId { get; set; }
}

public class TenantContext : ITenantContext
{
    private static readonly AsyncLocal<string?> _currentTenant = new();

    public string? TenantId
    {
        get => _currentTenant.Value;
        set => _currentTenant.Value = value;
    }
}

public class TenantMiddleware
{
    private readonly RequestDelegate _next;

    public TenantMiddleware(RequestDelegate next)
    {
        _next = next;
    }

    public async Task InvokeAsync(HttpContext context, ITenantContext tenantContext)
    {
        string? tenantId = context.Request.Headers["X-Tenant-ID"];
        if (string.IsNullOrWhiteSpace(tenantId))
        {
            tenantId = context.User?.FindFirst("tenant_id")?.Value;
        }

        tenantContext.TenantId = tenantId ?? "default";
        context.Items["TenantId"] = tenantContext.TenantId;

        await _next(context);
    }
}
