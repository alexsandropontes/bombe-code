"""
Testes para o snippet validar-cnpj
"""
import pytest
from snippet import validar_cnpj, formatar_cnpj


class TestValidarCNPJ:
    """Testes para função validar_cnpj"""
    
    def test_cnpj_valido_com_formatacao(self):
        """CNPJ válido com formatação"""
        assert validar_cnpj("34.028.316/0001-03") is True
    
    def test_cnpj_valido_sem_formatacao(self):
        """CNPJ válido sem formatação"""
        assert validar_cnpj("34028316000103") is True
    
    def test_cnpj_invalido(self):
        """CNPJ inválido"""
        assert validar_cnpj("12.345.678/0001-90") is False
    
    def test_cnpj_todos_digitos_iguais(self):
        """CNPJ com todos dígitos iguais é inválido"""
        assert validar_cnpj("11.111.111/1111-11") is False
        assert validar_cnpj("00000000000000") is False
    
    def test_cnpj_tamanho_invalido(self):
        """CNPJ com tamanho diferente de 14 dígitos"""
        assert validar_cnpj("34.028.316/0001") is False
        assert validar_cnpj("34028316000103123") is False


class TestFormatarCNPJ:
    """Testes para função formatar_cnpj"""
    
    def test_formatar_cnpj_valido(self):
        """Formata CNPJ válido"""
        assert formatar_cnpj("34028316000103") == "34.028.316/0001-03"
    
    def test_formatar_cnpj_ja_formatado(self):
        """CNPJ já formatado permanece igual"""
        assert formatar_cnpj("34.028.316/0001-03") == "34.028.316/0001-03"
    
    def test_formatar_cnpj_invalido(self):
        """CNPJ inválido retorna original"""
        assert formatar_cnpj("34028316") == "34028316"
