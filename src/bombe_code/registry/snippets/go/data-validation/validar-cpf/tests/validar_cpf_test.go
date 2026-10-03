package cpf

import "testing"

func TestValidarCPF(t *testing.T) {
	tests := []struct {
		name     string
		cpf      string
		expected bool
	}{
		{"CPF válido com formatação", "529.982.247-25", true},
		{"CPF válido sem formatação", "52998224725", true},
		{"CPF inválido", "123.456.789-09", false},
		{"CPF todos dígitos iguais", "11111111111", false},
		{"CPF tamanho inválido", "123456789", false},
		{"CPF com caracteres especiais", "529.982-247-25", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := ValidarCPF(tt.cpf)
			if result != tt.expected {
				t.Errorf("ValidarCPF(%q) = %v, expected %v", tt.cpf, result, tt.expected)
			}
		})
	}
}

func TestFormatarCPF(t *testing.T) {
	tests := []struct {
		name     string
		cpf      string
		expected string
	}{
		{"CPF válido sem formatação", "52998224725", "529.982.247-25"},
		{"CPF válido com formatação", "529.982.247-25", "529.982.247-25"},
		{"CPF inválido", "123456789", "123456789"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := FormatarCPF(tt.cpf)
			if result != tt.expected {
				t.Errorf("FormatarCPF(%q) = %q, expected %q", tt.cpf, result, tt.expected)
			}
		})
	}
}
