"""
Testes para o snippet format-cep
"""
import pytest
from snippet import formatar_cep, limpar_cep


class TestFormatarCEP:
    """Testes para função formatar_cep"""
    
    def test_formatar_cep_valido(self):
        """CEP válido com 8 dígitos"""
        assert formatar_cep("01234567") == "01234-567"
    
    def test_formatar_cep_ja_formatado(self):
        """CEP já formatado permanece igual"""
        assert formatar_cep("01234-567") == "01234-567"
    
    def test_formatar_cep_com_espaco(self):
        """CEP com espaço"""
        assert formatar_cep("01234 567") == "01234-567"
    
    def test_formatar_cep_tamanho_invalido(self):
        """CEP com tamanho inválido retorna original"""
        assert formatar_cep("1234567") == "1234567"
        assert formatar_cep("123456789") == "123456789"


class TestLimparCEP:
    """Testes para função limpar_cep"""
    
    def test_limpar_cep_formatado(self):
        """Remove formatação"""
        assert limpar_cep("01234-567") == "01234567"
    
    def test_limpar_cep_com_espaco(self):
        """Remove espaços"""
        assert limpar_cep("01234 567") == "01234567"
    
    def test_limpar_cep_ja_limpo(self):
        """CEP já limpo permanece igual"""
        assert limpar_cep("01234567") == "01234567"
