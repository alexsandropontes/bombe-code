"""
Testes para o snippet mask-credit-card
"""
import pytest
from snippet import mascarar_cartao, validar_luhn


class TestMascararCartao:
    """Testes para função mascarar_cartao"""
    
    def test_mascarar_cartao_valido(self):
        """Cartão válido com 16 dígitos"""
        assert mascarar_cartao("1234567890123456") == "**** **** **** 3456"
    
    def test_mascarar_cartao_com_espacos(self):
        """Cartão com espaços"""
        assert mascarar_cartao("1234 5678 9012 3456") == "**** **** **** 3456"
    
    def test_mascarar_cartao_com_tracos(self):
        """Cartão com traços"""
        assert mascarar_cartao("1234-5678-9012-3456") == "**** **** **** 3456"
    
    def test_mascarar_cartao_mostrar_2(self):
        """Mostrar apenas 2 últimos dígitos"""
        assert mascarar_cartao("1234567890123456", mostrar_ultimos=2) == "**** **** **** 56"
    
    def test_mascarar_cartao_tamanho_invalido(self):
        """Cartão com tamanho inválido retorna original"""
        assert mascarar_cartao("123456") == "123456"


class TestValidarLuhn:
    """Testes para função validar_luhn"""
    
    def test_luhn_cartao_valido(self):
        """Cartão válido pelo algoritmo de Luhn"""
        assert validar_luhn("4532015112830366") is True
    
    def test_luhn_cartao_invalido(self):
        """Cartão inválido pelo algoritmo de Luhn"""
        assert validar_luhn("1234567890123456") is False
    
    def test_luhn_cartao_com_espacos(self):
        """Cartão válido com espaços"""
        assert validar_luhn("4532 0151 1283 0366") is True
