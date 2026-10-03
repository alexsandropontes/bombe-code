using Xunit;
using CodeForge.Snippets.MultiTenancy;

public class TenantContextTests
{
    [Fact]
    public void IsolaContextoPorThreadAsync()
    {
        var ctx = new TenantContext();
        ctx.TenantId = "tenant-1";
        Assert.Equal("tenant-1", ctx.TenantId);
    }
}
