package uuid

import "testing"

func TestGerarUUID(t *testing.T) {
	t.Run("deve gerar UUID como string", func(t *testing.T) {
		resultado := GerarUUID()
		if len(resultado) == 0 {
			t.Error("UUID não pode ser vazio")
		}
	})

	t.Run("deve ter 36 caracteres", func(t *testing.T) {
		resultado := GerarUUID()
		if len(resultado) != 36 {
			t.Errorf("UUID deve ter 36 caracteres, got %d", len(resultado))
		}
	})

	t.Run("deve ter 4 hífens", func(t *testing.T) {
		resultado := GerarUUID()
		count := 0
		for _, r := range resultado {
			if r == '-' {
				count++
			}
		}
		if count != 4 {
			t.Errorf("UUID deve ter 4 hífens, got %d", count)
		}
	})

	t.Run("deve gerar UUIDs únicos", func(t *testing.T) {
		uuid1 := GerarUUID()
		uuid2 := GerarUUID()
		if uuid1 == uuid2 {
			t.Error("UUIDs gerados devem ser únicos")
		}
	})
}

func TestGerarUUIDSemTracos(t *testing.T) {
	t.Run("deve ter 32 caracteres", func(t *testing.T) {
		resultado := GerarUUIDSemTracos()
		if len(resultado) != 32 {
			t.Errorf("UUID sem traços deve ter 32 caracteres, got %d", len(resultado))
		}
	})

	t.Run("não deve conter hífen", func(t *testing.T) {
		resultado := GerarUUIDSemTracos()
		for _, r := range resultado {
			if r == '-' {
				t.Error("UUID sem traços não deve conter hífen")
			}
		}
	})
}

func TestValidarUUID(t *testing.T) {
	tests := []struct {
		name     string
		uuid     string
		expected bool
	}{
		{"UUID válido", "550e8400-e29b-41d4-a716-446655440000", true},
		{"UUID inválido", "not-a-uuid", false},
		{"String vazia", "", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := ValidarUUID(tt.uuid)
			if result != tt.expected {
				t.Errorf("ValidarUUID(%q) = %v, expected %v", tt.uuid, result, tt.expected)
			}
		})
	}
}
