// Package cpf fornece funções para validação e formatação de CPF brasileiro.
package cpf

import "strings"

// ValidarCPF valida um CPF brasileiro verificando os dígitos verificadores.
// Retorna true se o CPF for válido, false caso contrário.
// Aceita CPF formatado (com pontos e traço) ou apenas números.
//
// Exemplo:
//
//	valido := ValidarCPF("529.982.247-25") // true
//	valido := ValidarCPF("52998224725")    // true
//	valido := ValidarCPF("123.456.789-09") // false
func ValidarCPF(cpf string) bool {
	// Remove caracteres não numéricos
	cpf = strings.Map(func(r rune) rune {
		if r >= '0' && r <= '9' {
			return r
		}
		return -1
	}, cpf)

	// Verifica se tem 11 dígitos
	if len(cpf) != 11 {
		return false
	}

	// Verifica se todos os dígitos são iguais
	if allSame(cpf) {
		return false
	}

	// Valida primeiro dígito verificador
	digito1 := calcularDigito(cpf[:9], 10)
	if int(cpf[9]-'0') != digito1 {
		return false
	}

	// Valida segundo dígito verificador
	digito2 := calcularDigito(cpf[:10], 11)
	return int(cpf[10]-'0') == digito2
}

// FormatarCPF formata um CPF no padrão XXX.XXX.XXX-XX.
// Retorna o CPF formatado ou o original se tiver tamanho inválido.
//
// Exemplo:
//
//	formatado := FormatarCPF("52998224725") // "529.982.247-25"
func FormatarCPF(cpf string) string {
	// Remove caracteres não numéricos
	cpf = strings.Map(func(r rune) rune {
		if r >= '0' && r <= '9' {
			return r
		}
		return -1
	}, cpf)

	if len(cpf) != 11 {
		return cpf
	}

	return cpf[:3] + "." + cpf[3:6] + "." + cpf[6:9] + "-" + cpf[9:]
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

// calcularDigito calcula um dígito verificador do CPF.
// weights é o peso inicial (10 para primeiro dígito, 11 para o segundo).
func calcularDigito(cpf string, weights int) int {
	soma := 0
	for i, char := range cpf {
		soma += int(char-'0') * (weights - i)
	}
	resto := soma % 11
	if resto < 2 {
		return 0
	}
	return 11 - resto
}
