"""
Testes para o snippet validar-email
"""
import pytest
from snippet import validar_email, normalizar_email


class TestValidarEmail:
    """Testes para função validar_email"""
    
    def test_email_valido(self):
        """Email válido"""
        assert validar_email("usuario@exemplo.com") is True
    
    def test_email_com_ponto(self):
        """Email com ponto no nome"""
        assert validar_email("usuario.nome@exemplo.com") is True
    
    def test_email_com_mais(self):
        """Email com + (gmail style)"""
        assert validar_email("usuario+tag@exemplo.com") is True
    
    def test_email_com_sublinhado(self):
        """Email com sublinhado"""
        assert validar_email("usuario_nome@exemplo.com") is True
    
    def test_email_invalido_sem_arroba(self):
        """Email sem @ é inválido"""
        assert validar_email("email-invalido") is False
    
    def test_email_invalido_sem_dominio(self):
        """Email sem domínio é inválido"""
        assert validar_email("usuario@") is False
    
    def test_email_invalido_sem_tld(self):
        """Email sem TLD é inválido"""
        assert validar_email("usuario@exemplo") is False
    
    def test_email_invalido_espaco(self):
        """Email com espaço é inválido"""
        assert validar_email("usuario @exemplo.com") is False


class TestNormalizarEmail:
    """Testes para função normalizar_email"""
    
    def test_normalizar_maiusculas(self):
        """Converte para lowercase"""
        assert normalizar_email("Usuario@EXEMPLO.com") == "usuario@exemplo.com"
    
    def test_normalizar_com_espacos(self):
        """Remove espaços"""
        assert normalizar_email("  usuario@exemplo.com  ") == "usuario@exemplo.com"
    
    def test_normalizar_ja_minusculo(self):
        """Email já em lowercase permanece igual"""
        assert normalizar_email("usuario@exemplo.com") == "usuario@exemplo.com"
