"""
Testes para o snippet slugify
"""
import pytest
from snippet import slugify


class TestSlugify:
    """Testes para função slugify"""
    
    def test_slugify_texto_simples(self):
        """Texto simples sem acentos"""
        assert slugify("ola mundo") == "ola-mundo"
    
    def test_slugify_com_acentos(self):
        """Texto com acentos"""
        assert slugify("Olá Mundo!") == "ola-mundo"
        assert slugify("Python é Ótimo!") == "python-e-otimo"
    
    def test_slugify_com_caracteres_especiais(self):
        """Texto com caracteres especiais"""
        assert slugify("C++ vs C#") == "c-vs-c"
    
    def test_slugify_com_separador_custom(self):
        """Usar separador customizado"""
        assert slugify("Olá Mundo", separador='_') == "ola_mundo"
    
    def test_slugify_texto_com_espacos_multiplos(self):
        """Texto com múltiplos espaços"""
        assert slugify("Olá    Mundo") == "ola-mundo"
    
    def test_slugify_texto_com_hifens(self):
        """Texto já com hífens"""
        assert slugify("ola-mundo") == "ola-mundo"
    
    def test_slugify_texto_vazio(self):
        """Texto vazio retorna vazio"""
        assert slugify("") == ""
    
    def test_slugify_maiusculas(self):
        """Texto em maiúsculas"""
        assert slugify("OLÁ MUNDO") == "ola-mundo"
