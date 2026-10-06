"""
Testes para o snippet validar-cpf
"""
import pytest
from snippet import validar_cpf, formatar_cpf


class TestValidarCPF:
    """Testes para função validar_cpf"""

    def test_validar_cpf(self):
        """Validação básica de CPF"""
        assert validar_cpf("529.982.247-25") is True

    def test_cpf_valido_com_pontos_e_traco(self):
        """CPF válido com formatação"""
        assert validar_cpf("529.982.247-25") is True
    
    def test_cpf_valido_sem_formatacao(self):
        """CPF válido sem formatação"""
        assert validar_cpf("52998224725") is True
    
    def test_cpf_invalido(self):
        """CPF inválido"""
        assert validar_cpf("123.456.789-09") is False
    
    def test_cpf_todos_digitos_iguais(self):
        """CPF com todos dígitos iguais é inválido"""
        assert validar_cpf("111.111.111-11") is False
        assert validar_cpf("00000000000") is False
    
    def test_cpf_tamanho_invalido(self):
        """CPF com tamanho diferente de 11 dígitos"""
        assert validar_cpf("123.456.789") is False
        assert validar_cpf("1234567890123") is False
    
    def test_cpf_com_caracteres_especiais(self):
        """CPF com caracteres especiais que devem ser removidos"""
        assert validar_cpf("529.982-247-25") is True


class TestFormatarCPF:
    """Testes para função formatar_cpf"""
    
    def test_formatar_cpf_valido(self):
        """Formata CPF válido"""
        assert formatar_cpf("52998224725") == "529.982.247-25"
    
    def test_formatar_cpf_ja_formatado(self):
        """CPF já formatado permanece igual"""
        assert formatar_cpf("529.982.247-25") == "529.982.247-25"
    
    def test_formatar_cpf_invalido(self):
        """CPF inválido retorna original"""
        assert formatar_cpf("123456789") == "123456789"
