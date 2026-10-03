using Xunit;
using CodeForge.Snippets.Utils;
using System;
public class UuidGeneratorTests {
    [Fact]
    public void CriaGuidsValidos() {
        Assert.True(Guid.TryParse(UuidGenerator.NewV4(), out _));
        Assert.True(Guid.TryParse(UuidGenerator.NewV7(), out _));
    }
}
