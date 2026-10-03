namespace CodeForge.Snippets.Validation;

using System;
using System.Linq;

public static class CnpjValidator
{
    private static readonly int[] Multipliers1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    private static readonly int[] Multipliers2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

    public static bool Validar(string? cnpj)
    {
        if (string.IsNullOrWhiteSpace(cnpj)) return false;
        var digits = new string(cnpj.Where(char.IsDigit).ToArray());
        if (digits.Length != 14) return false;
        if (digits.Distinct().Count() == 1) return false;

        int sum1 = 0;
        for (int i = 0; i < 12; i++) sum1 += (digits[i] - '0') * Multipliers1[i];
        int rem1 = sum1 % 11;
        int d1 = rem1 < 2 ? 0 : 11 - rem1;
        if (digits[12] - '0' != d1) return false;

        int sum2 = 0;
        for (int i = 0; i < 13; i++) sum2 += (digits[i] - '0') * Multipliers2[i];
        int rem2 = sum2 % 11;
        int d2 = rem2 < 2 ? 0 : 11 - rem2;
        return digits[13] - '0' == d2;
    }

    public static string Formatar(string? cnpj)
    {
        if (string.IsNullOrWhiteSpace(cnpj)) return string.Empty;
        var clean = new string(cnpj.Where(char.IsDigit).ToArray());
        if (clean.Length != 14) return cnpj;
        return $"{clean[..2]}.{clean[2..5]}.{clean[5..8]}/{clean[8..12]}-{clean[12..]}";
    }
}
