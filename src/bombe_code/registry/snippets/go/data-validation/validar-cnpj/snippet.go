// Package cnpj fornece funções para validação e formatação de CNPJ brasileiro.
package cnpj

import "strings"

// ValidarCNPJ valida um CNPJ brasileiro verificando os dígitos verificadores.
// Retorna true se o CNPJ for válido, false caso contrário.
// Aceita CNPJ formatado (com pontos e traço) ou apenas números.
//
// Exemplo:
//
//	valido := ValidarCNPJ("34.028.316/0001-03") // true
//	valido := ValidarCNPJ("34028316000103")     // true
//	valido := ValidarCNPJ("12.345.678/0001-90") // false
func ValidarCNPJ(cnpj string) bool {
	// Remove caracteres não numéricos
	cnpj = strings.Map(func(r rune) rune {
		if r >= '0' && r <= '9' {
			return r
		}
		return -1
	}, cnpj)

	// Verifica se tem 14 dígitos
	if len(cnpj) != 14 {
		return false
	}

	// Verifica se todos os dígitos são iguais
	if allSame(cnpj) {
		return false
	}

	// Valida primeiro dígito verificador
	pesos1 := []int{5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2}
	digito1 := calcularDigito(cnpj[:12], pesos1)
	if int(cnpj[12]-'0') != digito1 {
		return false
	}

	// Valida segundo dígito verificador
	pesos2 := []int{6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2}
	digito2 := calcularDigito(cnpj[:13], pesos2)
	return int(cnpj[13]-'0') == digito2
}

// FormatarCNPJ formata um CNPJ no padrão XX.XXX.XXX/XXXX-XX.
// Retorna o CNPJ formatado ou o original se tiver tamanho inválido.
//
// Exemplo:
//
//	formatado := FormatarCNPJ("34028316000103") // "34.028.316/0001-03"
func FormatarCNPJ(cnpj string) string {
	// Remove caracteres não numéricos
	cnpj = strings.Map(func(r rune) rune {
		if r >= '0' && r <= '9' {
			return r
		}
		return -1
	}, cnpj)

	if len(cnpj) != 14 {
		return cnpj
	}

	return cnpj[:2] + "." + cnpj[2:5] + "." + cnpj[5:8] + "/" + cnpj[8:12] + "-" + cnpj[12:]
}

// allSame verifica se todos os caracteres de uma string são iguais.
func allSame(s string) bool {
	if len(s) == 0 {
		return false
	}
	first := s[0]
	for i := 1; i < len(s); i++ {
		if s[i] != first {
			return false
		}
	}
	return true
}

// calcularDigito calcula um dígito verificador do CNPJ.
func calcularDigito(cnpj string, pesos []int) int {
	soma := 0
	for i, char := range cnpj {
		soma += int(char-'0') * pesos[i]
	}
	resto := soma % 11
	if resto < 2 {
		return 0
	}
	return 11 - resto
}
