package creditcard

import "testing"

func TestMascararCartao(t *testing.T) {
	tests := []struct {
		name         string
		cartao       string
		mostrarUltimos int
		expected     string
	}{
		{"Cartão válido 16 dígitos", "1234567890123456", 4, "**** **** **** 3456"},
		{"Cartão com espaços", "1234 5678 9012 3456", 4, "**** **** **** 3456"},
		{"Cartão com traços", "1234-5678-9012-3456", 4, "**** **** **** 3456"},
		{"Mostrar 2 últimos", "1234567890123456", 2, "**** **** **** 56"},
		{"Tamanho inválido", "123456", 4, "123456"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := MascararCartao(tt.cartao, tt.mostrarUltimos)
			if result != tt.expected {
				t.Errorf("MascararCartao(%q, %d) = %q, expected %q", tt.cartao, tt.mostrarUltimos, result, tt.expected)
			}
		})
	}
}

func TestValidarLuhn(t *testing.T) {
	tests := []struct {
		name     string
		cartao   string
		expected bool
	}{
		{"Cartão válido", "4532015112830366", true},
		{"Cartão inválido", "1234567890123456", false},
		{"Cartão com espaços", "4532 0151 1283 0366", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := ValidarLuhn(tt.cartao)
			if result != tt.expected {
				t.Errorf("ValidarLuhn(%q) = %v, expected %v", tt.cartao, result, tt.expected)
			}
		})
	}
}
