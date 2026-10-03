using Xunit;
using CodeForge.Snippets.Omnichannel;
using System.Security.Cryptography;
using System.Text;

public class WhatsAppWebhookValidatorTests
{
    [Fact]
    public void ValidaAssinaturaCorretamente()
    {
        string secret = "secret123";
        string payload = "{\"entry\":[]}";
        using var hmac = new HMACSHA256(Encoding.UTF8.GetBytes(secret));
        string hash = "sha256=" + Convert.ToHexString(hmac.ComputeHash(Encoding.UTF8.GetBytes(payload))).ToLower();

        Assert.True(WhatsAppWebhookValidator.VerifySignature(payload, hash, secret));
        Assert.False(WhatsAppWebhookValidator.VerifySignature(payload, "sha256=invalid", secret));
    }
}
