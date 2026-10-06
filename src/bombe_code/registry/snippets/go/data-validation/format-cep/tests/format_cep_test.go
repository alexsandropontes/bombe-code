package cep

import "testing"

func TestFormatarCEP(t *testing.T) {
	tests := []struct {
		name     string
		cep      string
		expected string
	}{
		{"CEP válido 8 dígitos", "01234567", "01234-567"},
		{"CEP já formatado", "01234-567", "01234-567"},
		{"CEP com espaço", "01234 567", "01234-567"},
		{"CEP tamanho inválido", "1234567", "1234567"},
		{"CEP tamanho inválido grande", "123456789", "123456789"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := FormatarCEP(tt.cep)
			if result != tt.expected {
				t.Errorf("FormatarCEP(%q) = %q, expected %q", tt.cep, result, tt.expected)
			}
		})
	}
}

func TestLimparCEP(t *testing.T) {
	tests := []struct {
		name     string
		cep      string
		expected string
	}{
		{"CEP formatado", "01234-567", "01234567"},
		{"CEP com espaços", "01234 567", "01234567"},
		{"CEP já limpo", "01234567", "01234567"},
		{"CEP com traços", "01234-567", "01234567"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := LimparCEP(tt.cep)
			if result != tt.expected {
				t.Errorf("LimparCEP(%q) = %q, expected %q", tt.cep, result, tt.expected)
			}
		})
	}
}
