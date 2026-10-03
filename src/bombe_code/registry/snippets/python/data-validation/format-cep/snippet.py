"""
Formatador de CEP Brasileiro
Snippet oficial do Code Forge 2
"""


def formatar_cep(cep: str) -> str:
    """
    Formata CEP no padrão XXXXX-XXX.
    
    Args:
        cep: CEP como string (pode conter caracteres especiais)
    
    Returns:
        CEP formatado ou original se inválido
    
    Examples:
        >>> formatar_cep("01234567")
        '01234-567'
        >>> formatar_cep("01234-567")
        '01234-567'
    """
    # Remove caracteres não numéricos
    cep = ''.join(filter(str.isdigit, cep))
    
    # Verifica tamanho (8 dígitos)
    if len(cep) == 8:
        return f"{cep[:5]}-{cep[5:]}"
    else:
        # Tamanho inválido, retorna original
        return cep


def limpar_cep(cep: str) -> str:
    """
    Remove todos os caracteres não numéricos do CEP.
    
    Args:
        cep: CEP como string (pode conter caracteres especiais)
    
    Returns:
        Apenas dígitos
    
    Examples:
        >>> limpar_cep("01234-567")
        '01234567'
    """
    return ''.join(filter(str.isdigit, cep))
