// Package phone fornece funções para formatação de telefone brasileiro.
package phone

import (
	"strings"
	"unicode"
)

// FormatarTelefone formata um telefone no padrão (XX) XXXXX-XXXX.
// Funciona com 10 ou 11 dígitos (com ou sem 9º dígito).
// Retorna o telefone formatado ou o original se tiver tamanho inválido.
//
// Exemplo:
//
//	formatado := FormatarTelefone("11987654321") // "(11) 98765-4321"
//	formatado := FormatarTelefone("1138765432")  // "(11) 3876-5432"
func FormatarTelefone(telefone string) string {
	// Remove caracteres não numéricos
	telefone = LimparTelefone(telefone)

	// Verifica tamanho e formata
	switch len(telefone) {
	case 11:
		// Celular: (XX) XXXXX-XXXX
		return "(" + telefone[:2] + ") " + telefone[2:7] + "-" + telefone[7:]
	case 10:
		// Fixo: (XX) XXXX-XXXX
		return "(" + telefone[:2] + ") " + telefone[2:6] + "-" + telefone[6:]
	default:
		// Tamanho inválido, retorna original
		return telefone
	}
}

// LimparTelefone remove todos os caracteres não numéricos do telefone.
//
// Exemplo:
//
//	limpo := LimparTelefone("(11) 98765-4321") // "11987654321"
func LimparTelefone(telefone string) string {
	var builder strings.Builder
	for _, r := range telefone {
		if unicode.IsDigit(r) {
			builder.WriteRune(r)
		}
	}
	return builder.String()
}
