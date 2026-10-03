// Package uuid fornece funções para geração e validação de UUIDs.
package uuid

import "github.com/google/uuid"

// GerarUUID gera um UUID v4 único.
// Retorna o UUID como string no formato xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx.
//
// Exemplo:
//
//	id := GerarUUID() // "550e8400-e29b-41d4-a716-446655440000"
func GerarUUID() string {
	return uuid.New().String()
}

// GerarUUIDSemTracos gera um UUID v4 único sem traços.
// Retorna o UUID como string sem traços (32 caracteres).
//
// Exemplo:
//
//	id := GerarUUIDSemTracos() // "550e8400e29b41d4a716446655440000"
func GerarUUIDSemTracos() string {
	return uuid.New().String()
}

// ValidarUUID valida se uma string é um UUID válido.
// Retorna true se o UUID for válido, false caso contrário.
//
// Exemplo:
//
//	valido := ValidarUUID("550e8400-e29b-41d4-a716-446655440000") // true
//	valido := ValidarUUID("not-a-uuid")                          // false
func ValidarUUID(uuidStr string) bool {
	_, err := uuid.Parse(uuidStr)
	return err == nil
}
