using Xunit;
using CodeForge.Snippets.Auth;
using System.Security.Claims;

public class JwtTokenServiceTests
{
    private const string Secret = "super-secret-key-that-is-at-least-32-chars-long-123456";

    [Fact]
    public void GenerateAndValidateToken()
    {
        var service = new JwtTokenService(Secret);
        var token = service.GenerateToken("user-1", "Admin", "tenant-alpha");
        Assert.NotNull(token);

        var principal = service.ValidateToken(token);
        Assert.NotNull(principal);
        Assert.Equal("user-1", principal.FindFirst(ClaimTypes.NameIdentifier)?.Value ?? principal.FindFirst("sub")?.Value);
        Assert.Equal("Admin", principal.FindFirst(ClaimTypes.Role)?.Value);
        Assert.Equal("tenant-alpha", principal.FindFirst("tenant_id")?.Value);
    }
}
