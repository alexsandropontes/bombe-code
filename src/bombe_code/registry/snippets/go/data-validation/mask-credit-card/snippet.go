// Package creditcard fornece funções para máscara e validação de cartões de crédito.
package creditcard

import (
	"strings"
	"unicode"
)

// MascararCartao mascara um número de cartão de crédito, mostrando apenas os últimos dígitos.
// Retorna o cartão mascarado no formato **** **** **** 1234.
//
// Exemplo:
//
//	mascarado := MascararCartao("1234567890123456", 4) // "**** **** **** 3456"
func MascararCartao(cartao string, mostrarUltimos int) string {
	// Remove caracteres não numéricos
	cartao = LimparCartao(cartao)

	// Verifica tamanho (13-19 dígitos é o padrão de cartões)
	if len(cartao) < 13 || len(cartao) > 19 {
		return cartao
	}

	// Calcula quantos dígitos mascarar
	totalMascarar := len(cartao) - mostrarUltimos

	// Cria a parte mascarada
	mascarado := strings.Repeat("*", totalMascarar)

	// Pega os últimos dígitos
	ultimos := cartao[len(cartao)-mostrarUltimos:]

	// Junta e formata em grupos de 4
	completo := mascarado + ultimos

	var grupos []string
	for i := 0; i < len(completo); i += 4 {
		fim := i + 4
		if fim > len(completo) {
			fim = len(completo)
		}
		grupos = append(grupos, completo[i:fim])
	}

	return strings.Join(grupos, " ")
}

// ValidarLuhn valida um número de cartão usando o algoritmo de Luhn.
// Retorna true se o cartão for válido, false caso contrário.
//
// Exemplo:
//
//	valido := ValidarLuhn("4532015112830366") // true
func ValidarLuhn(cartao string) bool {
	// Remove caracteres não numéricos
	cartao = LimparCartao(cartao)

	// Inverte os dígitos
	digitos := make([]int, len(cartao))
	for i, r := range cartao {
		digitos[len(cartao)-1-i] = int(r - '0')
	}

	// Aplica algoritmo de Luhn
	soma := 0
	for i, digito := range digitos {
		if i%2 == 1 {
			digito *= 2
			if digito > 9 {
				digito -= 9
			}
		}
		soma += digito
	}

	return soma%10 == 0
}

// LimparCartao remove todos os caracteres não numéricos do cartão.
func LimparCartao(cartao string) string {
	var builder strings.Builder
	for _, r := range cartao {
		if unicode.IsDigit(r) {
			builder.WriteRune(r)
		}
	}
	return builder.String()
}
