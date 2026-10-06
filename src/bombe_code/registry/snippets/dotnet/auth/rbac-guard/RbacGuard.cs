namespace CodeForge.Snippets.Auth;

using System;
using System.Linq;
using System.Security.Claims;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;

[AttributeUsage(AttributeTargets.Class | AttributeTargets.Method)]
public class RequireRoleAttribute : TypeFilterAttribute
{
    public RequireRoleAttribute(params string[] roles) : base(typeof(RbacAuthorizationFilter))
    {
        Arguments = [roles];
    }
}

public class RbacAuthorizationFilter : IAuthorizationFilter
{
    private readonly string[] _roles;

    public RbacAuthorizationFilter(string[] roles)
    {
        _roles = roles;
    }

    public void OnAuthorization(AuthorizationFilterContext context)
    {
        var user = context.HttpContext.User;
        if (user == null || !user.Identity?.IsAuthenticated == true)
        {
            context.Result = new UnauthorizedObjectResult(new { ok = false, erro = "Autenticação requerida." });
            return;
        }

        var userRoles = user.FindAll(ClaimTypes.Role).Select(c => c.Value).ToHashSet(StringComparer.OrdinalIgnoreCase);
        bool hasRole = _roles.Any(role => userRoles.Contains(role));

        if (!hasRole)
        {
            context.Result = new ObjectResult(new { ok = false, erro = "Acesso negado: permissões insuficientes." })
            {
                StatusCode = 403
            };
        }
    }
}
