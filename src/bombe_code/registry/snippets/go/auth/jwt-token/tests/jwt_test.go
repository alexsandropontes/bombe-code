package auth
import (
	"testing"
	"time"
)
func TestJwt(t *testing.T) {
	secret := "secret-key-32-chars-length-12345"
	tok, err := GenerateToken(secret, "u1", "admin", "t1", time.Hour)
	if err != nil { t.Fatal(err) }
	c, err := ValidateToken(secret, tok)
	if err != nil || c.Sub != "u1" { t.Fatal("validação falhou") }
}
