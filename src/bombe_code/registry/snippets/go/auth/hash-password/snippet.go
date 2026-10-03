// Package hashpassword fornece funções para hash e verificação de senhas.
package hashpassword

import (
	"golang.org/x/crypto/bcrypt"
)

// HashSenha gera hash de senha usando bcrypt com salt automático.
// O custo padrão é 12 (recomendado para maioria dos casos).
//
// Exemplo:
//
//	hash, err := HashSenha("minha_senha_forte", 12)
//	if err != nil {
//	    // tratar erro
//	}
func HashSenha(senha string, custo int) (string, error) {
	if custo < 4 || custo > 31 {
		custo = 12 // Valor padrão seguro
	}

	// Converte senha para bytes
	senhaBytes := []byte(senha)

	// Gera hash com salt automático
	hashBytes, err := bcrypt.GenerateFromPassword(senhaBytes, custo)
	if err != nil {
		return "", err
	}

	return string(hashBytes), nil
}

// VerificarSenha verifica se uma senha corresponde ao hash.
// Retorna true se a senha estiver correta, false caso contrário.
//
// Exemplo:
//
//	hash, _ := HashSenha("minha_senha", 12)
//	if VerificarSenha("minha_senha", hash) {
//	    // senha correta
//	} else {
//	    // senha incorreta
//	}
func VerificarSenha(senha string, hash string) bool {
	senhaBytes := []byte(senha)
	hashBytes := []byte(hash)

	err := bcrypt.CompareHashAndPassword(hashBytes, senhaBytes)
	return err == nil
}
