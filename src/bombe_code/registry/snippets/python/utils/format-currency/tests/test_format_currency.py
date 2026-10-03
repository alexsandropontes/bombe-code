"""
Testes para o snippet format-currency
"""
import pytest
from snippet import formatar_moeda, parse_moeda


class TestFormatarMoeda:
    """Testes para função formatar_moeda"""
    
    def test_formatar_moeda_valor_positivo(self):
        """Valor positivo"""
        assert formatar_moeda(1234.56) == "R$ 1.234,56"
    
    def test_formatar_moeda_valor_inteiro(self):
        """Valor inteiro"""
        assert formatar_moeda(1000) == "R$ 1.000,00"
    
    def test_formatar_moeda_valor_negativo(self):
        """Valor negativo"""
        assert formatar_moeda(-50.5) == "-R$ 50,50"
    
    def test_formatar_moeda_simbolo_custom(self):
        """Símbolo customizado"""
        assert formatar_moeda(1000, simbolo="US$") == "US$ 1.000,00"
    
    def test_formatar_moeda_zero(self):
        """Zero"""
        assert formatar_moeda(0) == "R$ 0,00"
    
    def test_formatar_moeda_centavos(self):
        """Apenas centavos"""
        assert formatar_moeda(0.99) == "R$ 0,99"


class TestParseMoeda:
    """Testes para função parse_moeda"""
    
    def test_parse_moeda_completo(self):
        """Moeda completa com separadores"""
        assert parse_moeda("R$ 1.234,56") == 1234.56
    
    def test_parse_moeda_sem_milhar(self):
        """Moeda sem separador de milhar"""
        assert parse_moeda("R$ 1000,00") == 1000.0
    
    def test_parse_moeda_simbolo_custom(self):
        """Símbolo customizado"""
        assert parse_moeda("US$ 1.000,00", simbolo="US$") == 1000.0
    
    def test_parse_moeda_com_espacos(self):
        """Moeda com espaços extras"""
        assert parse_moeda("  R$ 1.000,00  ") == 1000.0
