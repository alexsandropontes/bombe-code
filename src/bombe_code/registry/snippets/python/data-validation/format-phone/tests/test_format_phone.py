"""
Testes para o snippet format-phone
"""
import pytest
from snippet import formatar_telefone, limpar_telefone


class TestFormatarTelefone:
    """Testes para função formatar_telefone"""
    
    def test_formatar_celular_11_digitos(self):
        """Celular com 11 dígitos"""
        assert formatar_telefone("11987654321") == "(11) 98765-4321"
    
    def test_formatar_celular_com_formatacao(self):
        """Celular já formatado"""
        assert formatar_telefone("(11) 98765-4321") == "(11) 98765-4321"
    
    def test_formatar_fixo_10_digitos(self):
        """Telefone fixo com 10 dígitos"""
        assert formatar_telefone("1138765432") == "(11) 3876-5432"
    
    def test_formatar_fixo_com_formatacao(self):
        """Fixo já formatado"""
        assert formatar_telefone("(11) 3876-5432") == "(11) 3876-5432"
    
    def test_formatar_tamanho_invalido(self):
        """Telefone com tamanho inválido retorna original"""
        assert formatar_telefone("1234567") == "1234567"
        assert formatar_telefone("1234567890123") == "1234567890123"


class TestLimparTelefone:
    """Testes para função limpar_telefone"""
    
    def test_limpar_telefone_formatado(self):
        """Remove formatação"""
        assert limpar_telefone("(11) 98765-4321") == "11987654321"
    
    def test_limpar_telefone_com_espacos(self):
        """Remove espaços"""
        assert limpar_telefone("11 98765 4321") == "11987654321"
    
    def test_limpar_telefone_ja_limpo(self):
        """Telefone já limpo permanece igual"""
        assert limpar_telefone("11987654321") == "11987654321"
