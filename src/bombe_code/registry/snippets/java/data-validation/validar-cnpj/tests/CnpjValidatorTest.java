package com.codeforge.snippets.validation;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class CnpjValidatorTest {
    @Test void testCnpj() {
        assertTrue(CnpjValidator.validar("11.222.333/0001-81"));
        assertFalse(CnpjValidator.validar("00000000000000"));
    }
}
