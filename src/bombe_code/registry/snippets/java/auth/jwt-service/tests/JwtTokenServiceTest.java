package com.codeforge.snippets.auth;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class JwtTokenServiceTest {
    @Test
    void testTokenValidation() {
        JwtTokenService service = new JwtTokenService("super-secret-key-32-chars-long-12345", 3600);
        String token = service.generateToken("user1", "ADMIN", "tenantX");
        assertTrue(service.validateToken(token));
        assertFalse(service.validateToken(token + "tampered"));
    }
}
