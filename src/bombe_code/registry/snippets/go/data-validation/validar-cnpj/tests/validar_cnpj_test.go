package cnpj

import "testing"

func TestValidarCNPJ(t *testing.T) {
	tests := []struct {
		name     string
		cnpj     string
		expected bool
	}{
		{"CNPJ válido com formatação", "34.028.316/0001-03", true},
		{"CNPJ válido sem formatação", "34028316000103", true},
		{"CNPJ inválido", "12.345.678/0001-90", false},
		{"CNPJ todos dígitos iguais", "11111111111111", false},
		{"CNPJ tamanho inválido", "340283160001", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := ValidarCNPJ(tt.cnpj)
			if result != tt.expected {
				t.Errorf("ValidarCNPJ(%q) = %v, expected %v", tt.cnpj, result, tt.expected)
			}
		})
	}
}

func TestFormatarCNPJ(t *testing.T) {
	tests := []struct {
		name     string
		cnpj     string
		expected string
	}{
		{"CNPJ válido sem formatação", "34028316000103", "34.028.316/0001-03"},
		{"CNPJ válido com formatação", "34.028.316/0001-03", "34.028.316/0001-03"},
		{"CNPJ inválido", "34028316", "34028316"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := FormatarCNPJ(tt.cnpj)
			if result != tt.expected {
				t.Errorf("FormatarCNPJ(%q) = %q, expected %q", tt.cnpj, result, tt.expected)
			}
		})
	}
}
