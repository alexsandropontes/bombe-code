namespace CodeForge.Snippets.Validation;
using System.Text.RegularExpressions;

public static class EmailValidator
{
    private static readonly Regex Regex = new(@"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", RegexOptions.Compiled);
    public static bool Validar(string? email) => !string.IsNullOrWhiteSpace(email) && Regex.IsMatch(email) && !email.Contains("..");
}
