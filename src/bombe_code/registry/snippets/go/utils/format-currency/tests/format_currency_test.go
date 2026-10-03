package currency

import "testing"

func TestFormatarMoeda(t *testing.T) {
	tests := []struct {
		name     string
		valor    float64
		simbolo  string
		expected string
	}{
		{"Valor positivo", 1234.56, "R$", "R$ 1.234,56"},
		{"Valor inteiro", 1000, "R$", "R$ 1.000,00"},
		{"Zero", 0, "R$", "R$ 0,00"},
		{"Apenas centavos", 0.99, "R$", "R$ 0,99"},
		{"Símbolo customizado", 1000, "US$", "US$ 1.000,00"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := FormatarMoeda(tt.valor, tt.simbolo)
			if result != tt.expected {
				t.Errorf("FormatarMoeda(%v, %q) = %q, expected %q", tt.valor, tt.simbolo, result, tt.expected)
			}
		})
	}
}

func TestParseMoeda(t *testing.T) {
	tests := []struct {
		name     string
		texto    string
		simbolo  string
		expected float64
	}{
		{"Moeda completa", "R$ 1.234,56", "R$", 1234.56},
		{"Sem separador de milhar", "R$ 1000,00", "R$", 1000.0},
		{"Símbolo customizado", "US$ 1.000,00", "US$", 1000.0},
		{"Com espaços", "  R$ 1.000,00  ", "R$", 1000.0},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := ParseMoeda(tt.texto, tt.simbolo)
			if err != nil {
				t.Errorf("ParseMoeda retornou erro: %v", err)
			}
			if result != tt.expected {
				t.Errorf("ParseMoeda(%q, %q) = %v, expected %v", tt.texto, tt.simbolo, result, tt.expected)
			}
		})
	}
}
