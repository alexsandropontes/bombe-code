"""
Slugify - Conversor de Texto para Slug
Snippet oficial do Code Forge 2
"""
import re
import unicodedata


def slugify(texto: str, separador: str = '-') -> str:
    """
    Converte texto em slug para URLs.
    
    Args:
        texto: Texto original
        separador: Separador a ser usado (padrão: '-')
    
    Returns:
        Texto convertido em slug (lowercase, sem acentos, apenas alphanumeric)
    
    Examples:
        >>> slugify("Olá Mundo!")
        'ola-mundo'
        >>> slugify("Python é Ótimo!")
        'python-e-otimo'
        >>> slugify("Hello World", separador='_')
        'hello_world'
    """
    # Converte para lowercase
    texto = texto.lower()
    
    # Remove acentos
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ascii', 'ignore').decode('ascii')
    
    # Remove caracteres especiais (mantém apenas alphanumeric e espaços)
    texto = re.sub(r'[^a-z0-9\s]', '', texto)
    
    # Substitui espaços pelo separador
    texto = re.sub(r'[\s_]+', separador, texto)
    
    # Remove separadores duplicados
    texto = re.sub(f'{re.escape(separador)}+', separador, texto)
    
    # Remove separadores do início e fim
    texto = texto.strip(separador)
    
    return texto
