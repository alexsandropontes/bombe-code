using Xunit;
using CodeForge.Snippets.Auth;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.AspNetCore.Http;
using System.Security.Claims;

public class RbacGuardTests
{
    [Fact]
    public void RejeitaUsuarioSemRole()
    {
        var filter = new RbacAuthorizationFilter(["Admin"]);
        var httpContext = new DefaultHttpContext();
        var claims = new[] { new Claim(ClaimTypes.Role, "User") };
        httpContext.User = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test"));

        var context = new AuthorizationFilterContext(
            new ActionContext(httpContext, new(), new()),
            new List<IFilterMetadata>()
        );

        filter.OnAuthorization(context);
        var res = context.Result as ObjectResult;
        Assert.NotNull(res);
        Assert.Equal(403, res.StatusCode);
    }
}
