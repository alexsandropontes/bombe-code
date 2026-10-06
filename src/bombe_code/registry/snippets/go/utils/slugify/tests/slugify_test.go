package slugify

import "testing"

func TestSlugify(t *testing.T) {
	tests := []struct {
		name     string
		texto    string
		expected string
	}{
		{"Texto simples", "ola mundo", "ola-mundo"},
		{"Com acentos", "Olá Mundo!", "ola-mundo"},
		{"Com acentos 2", "Python é Ótimo!", "python-e-otimo"},
		{"Com caracteres especiais", "C++ vs C#", "c-vs-c"},
		{"Múltiplos espaços", "Olá    Mundo", "ola-mundo"},
		{"Já com hífens", "ola-mundo", "ola-mundo"},
		{"Texto vazio", "", ""},
		{"Maiúsculas", "OLÁ MUNDO", "ola-mundo"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := Slugify(tt.texto)
			if result != tt.expected {
				t.Errorf("Slugify(%q) = %q, expected %q", tt.texto, result, tt.expected)
			}
		})
	}
}

func TestSlugifyCustom(t *testing.T) {
	tests := []struct {
		name      string
		texto     string
		separador string
		expected  string
	}{
		{"Separador underscore", "Olá Mundo", "_", "ola_mundo"},
		{"Separador ponto", "Olá Mundo", ".", "ola.mundo"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := SlugifyCustom(tt.texto, tt.separador)
			if result != tt.expected {
				t.Errorf("SlugifyCustom(%q, %q) = %q, expected %q", tt.texto, tt.separador, result, tt.expected)
			}
		})
	}
}
