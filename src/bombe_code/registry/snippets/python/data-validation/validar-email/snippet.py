"""
Validador de Formato de Email
Snippet oficial do Code Forge 2
"""
import re


def validar_email(email: str) -> bool:
    """
    Valida formato de email conforme RFC 5322.
    
    Args:
        email: Email como string
    
    Returns:
        True se email válido, False otherwise
    
    Examples:
        >>> validar_email("usuario@exemplo.com")
        True
        >>> validar_email("email-invalido")
        False
    """
    # Padrão RFC 5322 simplificado (cobre 99% dos casos reais)
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return bool(re.match(padrao, email))


def normalizar_email(email: str) -> str:
    """
    Normaliza email para lowercase.
    
    Args:
        email: Email como string
    
    Returns:
        Email em lowercase
    
    Examples:
        >>> normalizar_email("Usuario@EXEMPLO.com")
        'usuario@exemplo.com'
    """
    return email.lower().strip()
