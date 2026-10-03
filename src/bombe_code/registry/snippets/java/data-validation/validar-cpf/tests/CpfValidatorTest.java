package com.codeforge.snippets.validation;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class CpfValidatorTest {
    @Test
    void testValidarCpf() {
        assertTrue(CpfValidator.validar("52998224725"));
        assertFalse(CpfValidator.validar("11111111111"));
        assertFalse(CpfValidator.validar("12345678909"));
        assertFalse(CpfValidator.validar(null));
    }
}
