package phone

import "testing"

func TestFormatarTelefone(t *testing.T) {
	tests := []struct {
		name     string
		telefone string
		expected string
	}{
		{"Celular 11 dígitos", "11987654321", "(11) 98765-4321"},
		{"Celular já formatado", "(11) 98765-4321", "(11) 98765-4321"},
		{"Fixo 10 dígitos", "1138765432", "(11) 3876-5432"},
		{"Fixo já formatado", "(11) 3876-5432", "(11) 3876-5432"},
		{"Tamanho inválido", "1234567", "1234567"},
		{"Tamanho inválido grande", "1234567890123", "1234567890123"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := FormatarTelefone(tt.telefone)
			if result != tt.expected {
				t.Errorf("FormatarTelefone(%q) = %q, expected %q", tt.telefone, result, tt.expected)
			}
		})
	}
}

func TestLimparTelefone(t *testing.T) {
	tests := []struct {
		name     string
		telefone string
		expected string
	}{
		{"Telefone formatado", "(11) 98765-4321", "11987654321"},
		{"Telefone com espaços", "11 98765 4321", "11987654321"},
		{"Telefone já limpo", "11987654321", "11987654321"},
		{"Telefone com traços", "11-98765-4321", "11987654321"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := LimparTelefone(tt.telefone)
			if result != tt.expected {
				t.Errorf("LimparTelefone(%q) = %q, expected %q", tt.telefone, result, tt.expected)
			}
		})
	}
}
