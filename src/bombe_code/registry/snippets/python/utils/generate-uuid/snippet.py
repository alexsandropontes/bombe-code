"""
Gerador de UUID v4
Snippet oficial do Code Forge 2
"""
import uuid


def gerar_uuid() -> str:
    """
    Gera um UUID v4 único.
    
    Returns:
        UUID como string no formato xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
    
    Examples:
        >>> uuid = gerar_uuid()
        >>> len(uuid) == 36
        True
    """
    return str(uuid.uuid4())


def gerar_uuid_sem_tracos() -> str:
    """
    Gera um UUID v4 único sem traços.
    
    Returns:
        UUID como string sem traços (32 caracteres)
    
    Examples:
        >>> uuid = gerar_uuid_sem_tracos()
        >>> len(uuid) == 32
        True
    """
    return uuid.uuid4().hex


def validar_uuid(uuid_str: str) -> bool:
    """
    Valida se uma string é um UUID válido.
    
    Args:
        uuid_str: String para validar
    
    Returns:
        True se UUID válido, False otherwise
    
    Examples:
        >>> validar_uuid("550e8400-e29b-41d4-a716-446655440000")
        True
        >>> validar_uuid("not-a-uuid")
        False
    """
    try:
        uuid.UUID(uuid_str)
        return True
    except ValueError:
        return False
