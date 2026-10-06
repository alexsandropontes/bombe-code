using Xunit;
using CodeForge.Snippets.Validation;

public class CnpjValidatorTests
{
    [Theory]
    [InlineData("11.222.333/0001-81", true)]
    [InlineData("00000000000000", false)]
    public void ValidaCnpj(string? cnpj, bool esperado)
    {
        Assert.Equal(esperado, CnpjValidator.Validar(cnpj));
    }
}
