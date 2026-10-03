package com.codeforge.snippets.auth;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class PasswordHasherTest {
    @Test void testHashVerify() {
        String h = PasswordHasher.hash("minhaSenha123");
        assertTrue(PasswordHasher.verify("minhaSenha123", h));
        assertFalse(PasswordHasher.verify("outraSenha", h));
    }
}
