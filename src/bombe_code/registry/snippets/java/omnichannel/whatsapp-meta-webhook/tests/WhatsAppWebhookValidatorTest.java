package com.codeforge.snippets.omnichannel;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class WhatsAppWebhookValidatorTest {
    @Test
    void testChallengeVerification() {
        assertEquals("challenge_token", WhatsAppWebhookValidator.verifyChallenge("subscribe", "my_token", "challenge_token", "my_token"));
        assertNull(WhatsAppWebhookValidator.verifyChallenge("subscribe", "wrong", "challenge_token", "my_token"));
    }
}
