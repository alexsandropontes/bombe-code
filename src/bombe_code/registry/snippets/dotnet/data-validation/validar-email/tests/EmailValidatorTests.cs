using Xunit;
using CodeForge.Snippets.Validation;
public class EmailValidatorTests {
    [Theory]
    [InlineData("dev@codeforge.com", true)]
    [InlineData("invalido", false)]
    [InlineData("a..b@c.com", false)]
    public void ValidaEmail(string email, bool esperado) => Assert.Equal(esperado, EmailValidator.Validar(email));
}
