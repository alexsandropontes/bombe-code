namespace CodeForge.Snippets.Utils;
using System;

public static class UuidGenerator
{
    public static string NewV4() => Guid.NewGuid().ToString("D");
    public static string NewV7() => Guid.CreateVersion7().ToString("D");
}
