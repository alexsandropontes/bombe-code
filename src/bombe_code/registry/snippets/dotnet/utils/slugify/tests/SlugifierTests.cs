using Xunit;
using CodeForge.Snippets.Utils;
public class SlugifierTests {
    [Fact]
    public void GeraSlugCorreto() {
        Assert.Equal("ola-mundo-do-csharp", Slugifier.Slugify("Olá, Mundo do C#!!"));
    }
}
