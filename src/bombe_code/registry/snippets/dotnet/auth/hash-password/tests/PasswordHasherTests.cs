using Xunit;
using CodeForge.Snippets.Auth;
public class PasswordHasherTests {
    [Fact]
    public void HashAndVerify() {
        string hash = PasswordHasher.HashPassword("senhaSegura123!");
        Assert.True(PasswordHasher.VerifyPassword("senhaSegura123!", hash));
        Assert.False(PasswordHasher.VerifyPassword("senhaErrada", hash));
    }
}
