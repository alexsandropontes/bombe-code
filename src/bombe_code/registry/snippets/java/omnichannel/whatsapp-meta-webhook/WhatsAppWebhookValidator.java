package com.codeforge.snippets.omnichannel;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

public final class WhatsAppWebhookValidator {
    private WhatsAppWebhookValidator() {}

    public static boolean verifySignature(String payload, String signatureHeader, String appSecret) {
        if (payload == null || signatureHeader == null || appSecret == null) return false;
        if (!signatureHeader.startsWith("sha256=")) return false;

        String expectedHash = signatureHeader.substring("sha256=".length()).trim();
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(appSecret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] hash = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
            String actualHash = HexFormat.of().formatHex(hash);

            return MessageDigest.isEqual(
                actualHash.toLowerCase().getBytes(StandardCharsets.UTF_8),
                expectedHash.toLowerCase().getBytes(StandardCharsets.UTF_8)
            );
        } catch (Exception e) {
            return false;
        }
    }

    public static String verifyChallenge(String mode, String token, String challenge, String expectedToken) {
        if ("subscribe".equals(mode) && expectedToken.equals(token)) {
            return challenge;
        }
        return null;
    }
}
