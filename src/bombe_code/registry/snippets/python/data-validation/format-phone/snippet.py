"""
Formatador de Telefone Brasileiro
Snippet oficial do Code Forge 2
"""


def formatar_telefone(telefone: str) -> str:
    """
    Formata telefone no padrão (XX) XXXXX-XXXX.
    Funciona com 10 ou 11 dígitos (com ou sem 9º dígito).
    
    Args:
        telefone: Telefone como string (pode conter caracteres especiais)
    
    Returns:
        Telefone formatado ou original se inválido
    
    Examples:
        >>> formatar_telefone("11987654321")
        '(11) 98765-4321'
        >>> formatar_telefone("1138765432")
        '(11) 3876-5432'
    """
    # Remove caracteres não numéricos
    telefone = ''.join(filter(str.isdigit, telefone))
    
    # Verifica tamanho
    if len(telefone) == 11:
        # Celular: (XX) XXXXX-XXXX
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    elif len(telefone) == 10:
        # Fixo: (XX) XXXX-XXXX
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    else:
        # Tamanho inválido, retorna original
        return telefone


def limpar_telefone(telefone: str) -> str:
    """
    Remove todos os caracteres não numéricos do telefone.
    
    Args:
        telefone: Telefone como string (pode conter caracteres especiais)
    
    Returns:
        Apenas dígitos
    
    Examples:
        >>> limpar_telefone("(11) 98765-4321")
        '11987654321'
    """
    return ''.join(filter(str.isdigit, telefone))
