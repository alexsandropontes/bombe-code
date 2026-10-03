package com.codeforge.snippets.auth;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

public class JwtTokenService {
    private final String secret;
    private final long expirationSeconds;

    public JwtTokenService(String secret, long expirationSeconds) {
        if (secret == null || secret.length() < 32) {
            throw new IllegalArgumentException("Secret JWT deve ter pelo menos 32 caracteres.");
        }
        this.secret = secret;
        this.expirationSeconds = expirationSeconds;
    }

    public String generateToken(String subject, String role, String tenantId) {
        long now = Instant.now().getEpochSecond();
        long exp = now + expirationSeconds;
        
        String header = Base64.getUrlEncoder().withoutPadding().encodeToString("{\"alg\":\"HS256\",\"typ\":\"JWT\"}".getBytes(StandardCharsets.UTF_8));
        String payloadJson = String.format("{\"sub\":\"%s\",\"role\":\"%s\",\"tenant_id\":\"%s\",\"iat\":%d,\"exp\":%d}",
                subject, role, tenantId != null ? tenantId : "default", now, exp);
        String payload = Base64.getUrlEncoder().withoutPadding().encodeToString(payloadJson.getBytes(StandardCharsets.UTF_8));
        
        String signature = sign(header + "." + payload, secret);
        return header + "." + payload + "." + signature;
    }

    public boolean validateToken(String token) {
        if (token == null || !token.contains(".")) return false;
        String[] parts = token.split("\\.");
        if (parts.length != 3) return false;

        String expectedSignature = sign(parts[0] + "." + parts[1], secret);
        if (!MessageDigest.isEqual(expectedSignature.getBytes(StandardCharsets.UTF_8), parts[2].getBytes(StandardCharsets.UTF_8))) {
            return false;
        }

        try {
            String payloadJson = new String(Base64.getUrlDecoder().decode(parts[1]), StandardCharsets.UTF_8);
            if (payloadJson.contains("\"exp\":")) {
                int expIdx = payloadJson.indexOf("\"exp\":") + 6;
                int endIdx = payloadJson.indexOf("}", expIdx);
                if (endIdx < 0) endIdx = payloadJson.indexOf(",", expIdx);
                long exp = Long.parseLong(payloadJson.substring(expIdx, endIdx).trim());
                return Instant.now().getEpochSecond() <= exp;
            }
        } catch (Exception e) {
            return false;
        }
        return true;
    }

    private String sign(String data, String key) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] raw = mac.doFinal(data.getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(raw);
        } catch (Exception e) {
            throw new RuntimeException("Erro ao assinar JWT", e);
        }
    }
}
