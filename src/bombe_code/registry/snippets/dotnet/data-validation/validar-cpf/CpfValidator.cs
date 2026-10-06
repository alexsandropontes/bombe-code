namespace CodeForge.Snippets.Validation;

using System;
using System.Linq;
using System.Text.RegularExpressions;

public static class CpfValidator
{
    public static bool Validar(string? cpf)
    {
        if (string.IsNullOrWhiteSpace(cpf)) return false;
        
        Span<char> digits = stackalloc char[11];
        int count = 0;
        foreach (char c in cpf)
        {
            if (char.IsDigit(c))
            {
                if (count >= 11) return false;
                digits[count++] = c;
            }
        }
        if (count != 11) return false;

        bool allSame = true;
        for (int i = 1; i < 11; i++)
        {
            if (digits[i] != digits[0]) { allSame = false; break; }
        }
        if (allSame) return false;

        int sum1 = 0;
        for (int i = 0; i < 9; i++) sum1 += (digits[i] - '0') * (10 - i);
        int rem1 = sum1 % 11;
        int d1 = rem1 < 2 ? 0 : 11 - rem1;
        if (digits[9] - '0' != d1) return false;

        int sum2 = 0;
        for (int i = 0; i < 10; i++) sum2 += (digits[i] - '0') * (11 - i);
        int rem2 = sum2 % 11;
        int d2 = rem2 < 2 ? 0 : 11 - rem2;
        return digits[10] - '0' == d2;
    }

    public static string Formatar(string? cpf)
    {
        if (string.IsNullOrWhiteSpace(cpf)) return string.Empty;
        var clean = new string(cpf.Where(char.IsDigit).ToArray());
        if (clean.Length != 11) return cpf;
        return $"{clean[..3]}.{clean[3..6]}.{clean[6..9]}-{clean[9..]}";
    }
}
