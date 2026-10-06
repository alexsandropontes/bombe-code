using Xunit;
using CodeForge.Snippets.Validation;

public class CpfValidatorTests
{
    [Theory]
    [InlineData("52998224725", true)]
    [InlineData("11111111111", false)]
    [InlineData("12345678909", false)]
    [InlineData("", false)]
    [InlineData(null, false)]
    public void ValidaCpfCorretamente(string? cpf, bool esperado)
    {
        Assert.Equal(esperado, CpfValidator.Validar(cpf));
    }
}
