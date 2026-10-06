package com.codeforge.snippets.multitenancy;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class TenantContextTest {
    @Test
    void testTenantContextIsolation() {
        TenantContext.setCurrentTenant("tenant-a");
        assertEquals("tenant-a", TenantContext.getCurrentTenant());
        TenantContext.clear();
        assertEquals("default", TenantContext.getCurrentTenant());
    }
}
