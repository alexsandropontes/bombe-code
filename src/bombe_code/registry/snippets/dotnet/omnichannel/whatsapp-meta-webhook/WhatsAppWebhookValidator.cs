namespace CodeForge.Snippets.Omnichannel;

using System;
using System.Security.Cryptography;
using System.Text;

public static class WhatsAppWebhookValidator
{
    public static bool VerifySignature(string payload, string signatureHeader, string appSecret)
    {
        if (string.IsNullOrWhiteSpace(payload) || string.IsNullOrWhiteSpace(signatureHeader) || string.IsNullOrWhiteSpace(appSecret))
            return false;

        const string prefix = "sha256=";
        if (!signatureHeader.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            return false;

        string expectedHash = signatureHeader[prefix.Length..];
        using var hmac = new HMACSHA256(Encoding.UTF8.GetBytes(appSecret));
        byte[] hash = hmac.ComputeHash(Encoding.UTF8.GetBytes(payload));
        string actualHash = Convert.ToHexString(hash).ToLowerInvariant();

        return CryptographicOperations.FixedTimeEquals(
            Encoding.UTF8.GetBytes(actualHash),
            Encoding.UTF8.GetBytes(expectedHash.ToLowerInvariant())
        );
    }

    public static string? VerifyHubChallenge(string mode, string verifyToken, string challenge, string expectedToken)
    {
        if (mode == "subscribe" && verifyToken == expectedToken)
        {
            return challenge;
        }
        return null;
    }
}
