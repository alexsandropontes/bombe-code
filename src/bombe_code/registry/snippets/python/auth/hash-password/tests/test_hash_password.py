"""
Testes para o snippet hash-password
"""
import pytest
from snippet import hash_senha, verificar_senha


class TestHashSenha:
    """Testes para função hash_senha"""
    
    def test_hash_senha_retorna_string(self):
        """Hash deve ser uma string"""
        resultado = hash_senha("teste123")
        assert isinstance(resultado, str)
    
    def test_hash_senha_comeca_com_prefixo_bcrypt(self):
        """Hash deve começar com $2b$"""
        resultado = hash_senha("teste123")
        assert resultado.startswith('$2b$12$')
    
    def test_hash_senha_diferente_para_mesma_senha(self):
        """Hash deve ser diferente a cada chamada (salt diferente)"""
        hash1 = hash_senha("teste123")
        hash2 = hash_senha("teste123")
        assert hash1 != hash2
    
    def test_hash_senha_com_rounds_customizado(self):
        """Hash deve funcionar com rounds customizado"""
        resultado = hash_senha("teste123", rounds=10)
        assert resultado.startswith('$2b$10$')


class TestVerificarSenha:
    """Testes para função verificar_senha"""
    
    def test_verificar_senha_correta(self):
        """Senha correta deve retornar True"""
        hash = hash_senha("teste123")
        assert verificar_senha("teste123", hash) is True
    
    def test_verificar_senha_incorreta(self):
        """Senha incorreta deve retornar False"""
        hash = hash_senha("teste123")
        assert verificar_senha("senha_errada", hash) is False
    
    def test_verificar_senha_com_caracteres_especiais(self):
        """Senha com caracteres especiais deve funcionar"""
        hash = hash_senha("tëste!@#$%123")
        assert verificar_senha("tëste!@#$%123", hash) is True
        assert verificar_senha("teste!@#$%123", hash) is False
