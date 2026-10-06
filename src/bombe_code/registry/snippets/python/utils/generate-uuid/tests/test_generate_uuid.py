"""
Testes para o snippet generate-uuid
"""
import pytest
from snippet import gerar_uuid, gerar_uuid_sem_tracos, validar_uuid


class TestGerarUUID:
    """Testes para função gerar_uuid"""
    
    def test_gerar_uuid_retorna_string(self):
        """UUID deve ser uma string"""
        resultado = gerar_uuid()
        assert isinstance(resultado, str)
    
    def test_gerar_uuid_tamanho(self):
        """UUID deve ter 36 caracteres (com traços)"""
        resultado = gerar_uuid()
        assert len(resultado) == 36
    
    def test_gerar_uuid_formato(self):
        """UUID deve seguir formato xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"""
        resultado = gerar_uuid()
        assert resultado.count('-') == 4
    
    def test_gerar_uuid_unicos(self):
        """UUIDs gerados devem ser únicos"""
        uuid1 = gerar_uuid()
        uuid2 = gerar_uuid()
        assert uuid1 != uuid2


class TestGerarUUIDSemTracos:
    """Testes para função gerar_uuid_sem_tracos"""
    
    def test_gerar_uuid_sem_tracos_tamanho(self):
        """UUID sem traços deve ter 32 caracteres"""
        resultado = gerar_uuid_sem_tracos()
        assert len(resultado) == 32
    
    def test_gerar_uuid_sem_tracos_sem_hifen(self):
        """UUID sem traços não deve conter hífen"""
        resultado = gerar_uuid_sem_tracos()
        assert '-' not in resultado


class TestValidarUUID:
    """Testes para função validar_uuid"""
    
    def test_validar_uuid_valido(self):
        """UUID válido deve retornar True"""
        assert validar_uuid("550e8400-e29b-41d4-a716-446655440000") is True
    
    def test_validar_uuid_invalido(self):
        """UUID inválido deve retornar False"""
        assert validar_uuid("not-a-uuid") is False
    
    def test_validar_uuid_vazio(self):
        """String vazia deve retornar False"""
        assert validar_uuid("") is False
