// Package cep fornece funções para formatação de CEP brasileiro.
package cep

import (
	"strings"
	"unicode"
)

// FormatarCEP formata um CEP no padrão XXXXX-XXX.
// Retorna o CEP formatado ou o original se tiver tamanho inválido.
//
// Exemplo:
//
//	formatado := FormatarCEP("01234567") // "01234-567"
func FormatarCEP(cep string) string {
	// Remove caracteres não numéricos
	cep = LimparCEP(cep)

	// Verifica tamanho (8 dígitos)
	if len(cep) == 8 {
		return cep[:5] + "-" + cep[5:]
	}

	// Tamanho inválido, retorna original
	return cep
}

// LimparCEP remove todos os caracteres não numéricos do CEP.
//
// Exemplo:
//
//	limpo := LimparCEP("01234-567") // "01234567"
func LimparCEP(cep string) string {
	var builder strings.Builder
	for _, r := range cep {
		if unicode.IsDigit(r) {
			builder.WriteRune(r)
		}
	}
	return builder.String()
}
