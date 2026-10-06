// Package currency fornece funções para formatação de moeda brasileira.
package currency

import (
	"fmt"
	"strings"
)

// FormatarMoeda formata um valor numérico como moeda brasileira.
// Retorna o valor formatado no padrão brasileiro (ex: "R$ 1.234,56").
//
// Exemplo:
//
//	formatado := FormatarMoeda(1234.56, "R$") // "R$ 1.234,56"
//	formatado := FormatarMoeda(1000, "R$")    // "R$ 1.000,00"
func FormatarMoeda(valor float64, simbolo string) string {
	// Formata com duas casas decimais
	formatado := fmt.Sprintf("%.2f", valor)

	// Adiciona separador de milhar
	var resultado strings.Builder
	parts := strings.Split(formatado, ".")
	inteiro := parts[0]
	decimal := parts[1]

	// Adiciona separador de milhar
	counter := 0
	for i := len(inteiro) - 1; i >= 0; i-- {
		if counter > 0 && counter%3 == 0 {
			resultado.WriteString(".")
		}
		resultado.WriteByte(inteiro[i])
		counter++
	}

	// Inverte o inteiro
	inteiroFormatado := Reverse(resultado.String())

	return fmt.Sprintf("%s %s,%s", simbolo, inteiroFormatado, decimal)
}

// ParseMoeda converte texto formatado como moeda para valor numérico.
// Retorna o valor numérico (ex: 1234.56).
//
// Exemplo:
//
//	valor := ParseMoeda("R$ 1.234,56", "R$") // 1234.56
func ParseMoeda(texto string, simbolo string) (float64, error) {
	// Remove símbolo e espaços
	texto = strings.ReplaceAll(texto, simbolo, "")
	texto = strings.TrimSpace(texto)

	// Remove separador de milhar
	texto = strings.ReplaceAll(texto, ".", "")

	// Converte separador decimal
	texto = strings.ReplaceAll(texto, ",", ".")

	var valor float64
	_, err := fmt.Sscanf(texto, "%f", &valor)
	if err != nil {
		return 0, err
	}

	return valor, nil
}

// Reverse inverte uma string.
func Reverse(s string) string {
	runes := []rune(s)
	for i, j := 0, len(runes)-1; i < j; i, j = i+1, j-1 {
		runes[i], runes[j] = runes[j], runes[i]
	}
	return string(runes)
}
