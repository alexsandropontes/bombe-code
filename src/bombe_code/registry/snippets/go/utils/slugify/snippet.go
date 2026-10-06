// Package slugify fornece funções para conversão de texto em slug.
package slugify

import "github.com/gosimple/slug"

// Slugify converte um texto em slug para URLs.
// Retorna o texto convertido em slug (lowercase, sem acentos, apenas alphanumeric).
//
// Exemplo:
//
//	slug := Slugify("Olá Mundo!") // "ola-mundo"
//	slug := Slugify("Python é Ótimo!") // "python-e-otimo"
func Slugify(texto string) string {
	return slug.Make(texto)
}

// SlugifyCustom converte um texto em slug com separador customizado.
// Retorna o texto convertido em slug usando o separador especificado.
//
// Exemplo:
//
//	slug := SlugifyCustom("Olá Mundo", "_") // "ola_mundo"
func SlugifyCustom(texto string, separador string) string {
	slug.CustomSub = map[string]string{
		" ": separador,
	}
	return slug.Make(texto)
}
