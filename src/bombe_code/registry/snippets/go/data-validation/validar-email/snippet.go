// Package email fornece funções para validação de formato de email.
package email

import (
	"net/mail"
	"strings"
)

// ValidarEmail valida um formato de email conforme RFC 5322.
// Retorna true se o email for válido, false caso contrário.
//
// Exemplo:
//
//	valido := ValidarEmail("usuario@exemplo.com") // true
//	valido := ValidarEmail("email-invalido")      // false
func ValidarEmail(email string) bool {
	// Usa o parser padrão do Go que segue RFC 5322
	_, err := mail.ParseAddress(email)
	if err != nil {
		return false
	}

	// Verifica se tem @ e domínio
	parts := strings.Split(email, "@")
	if len(parts) != 2 {
		return false
	}

	// Verifica se o domínio tem pelo menos um ponto
	domainParts := strings.Split(parts[1], ".")
	return len(domainParts) >= 2
}

// NormalizarEmail normaliza email para lowercase e remove espaços.
//
// Exemplo:
//
//	normalizado := NormalizarEmail("Usuario@EXEMPLO.com") // "usuario@exemplo.com"
func NormalizarEmail(email string) string {
	return strings.ToLower(strings.TrimSpace(email))
}
