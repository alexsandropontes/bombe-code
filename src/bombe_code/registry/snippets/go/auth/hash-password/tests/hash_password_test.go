package hashpassword

import (
	"testing"
)

func TestHashSenha(t *testing.T) {
	t.Run("deve gerar hash válido", func(t *testing.T) {
		hash, err := HashSenha("teste123", 12)
		if err != nil {
			t.Errorf("Erro inesperado: %v", err)
		}
		if len(hash) == 0 {
			t.Error("Hash não pode ser vazio")
		}
	})

	t.Run("deve gerar hash diferente para mesma senha", func(t *testing.T) {
		hash1, _ := HashSenha("teste123", 12)
		hash2, _ := HashSenha("teste123", 12)
		if hash1 == hash2 {
			t.Error("Hashes devem ser diferentes (salt diferente)")
		}
	})

	t.Run("deve usar custo customizado", func(t *testing.T) {
		hash, _ := HashSenha("teste123", 10)
		if len(hash) == 0 {
			t.Error("Hash não pode ser vazio")
		}
	})

	t.Run("deve usar custo padrão quando inválido", func(t *testing.T) {
		hash, _ := HashSenha("teste123", 1) // custo muito baixo
		if len(hash) == 0 {
			t.Error("Hash não pode ser vazio")
		}
	})
}

func TestVerificarSenha(t *testing.T) {
	t.Run("deve retornar true para senha correta", func(t *testing.T) {
		hash, _ := HashSenha("teste123", 12)
		if !VerificarSenha("teste123", hash) {
			t.Error("Deveria retornar true para senha correta")
		}
	})

	t.Run("deve retornar false para senha incorreta", func(t *testing.T) {
		hash, _ := HashSenha("teste123", 12)
		if VerificarSenha("senha_errada", hash) {
			t.Error("Deveria retornar false para senha incorreta")
		}
	})

	t.Run("deve funcionar com caracteres especiais", func(t *testing.T) {
		hash, _ := HashSenha("tëste!@#$%123", 12)
		if !VerificarSenha("tëste!@#$%123", hash) {
			t.Error("Deveria funcionar com caracteres especiais")
		}
		if VerificarSenha("teste!@#$%123", hash) {
			t.Error("Deveria retornar false para senha diferente")
		}
	})
}
