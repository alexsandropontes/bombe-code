package email

import "testing"

func TestValidarEmail(t *testing.T) {
	tests := []struct {
		name     string
		email    string
		expected bool
	}{
		{"Email válido", "usuario@exemplo.com", true},
		{"Email com ponto", "usuario.nome@exemplo.com", true},
		{"Email com +", "usuario+tag@exemplo.com", true},
		{"Email com sublinhado", "usuario_nome@exemplo.com", true},
		{"Email sem @", "email-invalido", false},
		{"Email sem domínio", "usuario@", false},
		{"Email sem TLD", "usuario@exemplo", false},
		{"Email com espaço", "usuario @exemplo.com", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := ValidarEmail(tt.email)
			if result != tt.expected {
				t.Errorf("ValidarEmail(%q) = %v, expected %v", tt.email, result, tt.expected)
			}
		})
	}
}

func TestNormalizarEmail(t *testing.T) {
	tests := []struct {
		name     string
		email    string
		expected string
	}{
		{"Converte para lowercase", "Usuario@EXEMPLO.com", "usuario@exemplo.com"},
		{"Remove espaços", "  usuario@exemplo.com  ", "usuario@exemplo.com"},
		{"Já em lowercase", "usuario@exemplo.com", "usuario@exemplo.com"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := NormalizarEmail(tt.email)
			if result != tt.expected {
				t.Errorf("NormalizarEmail(%q) = %q, expected %q", tt.email, result, tt.expected)
			}
		})
	}
}
