"""
Formatador de Moeda Brasileira (R$)
Snippet oficial do Code Forge 2
"""


def formatar_moeda(valor: float, simbolo: str = "R$") -> str:
    """
    Formata um valor numérico como moeda brasileira.
    
    Args:
        valor: Valor numérico (ex: 1234.56)
        simbolo: Símbolo da moeda (padrão: "R$")
    
    Returns:
        Valor formatado no padrão brasileiro (ex: "R$ 1.234,56")
    
    Examples:
        >>> formatar_moeda(1234.56)
        'R$ 1.234,56'
        >>> formatar_moeda(1000)
        'R$ 1.000,00'
        >>> formatar_moeda(-50.5, simbolo="US$")
        '-US$ 50,50'
    """
    # Formata com separadores brasileiros
    valor_formatado = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    return f"{simbolo} {valor_formatado}"


def parse_moeda(texto: str, simbolo: str = "R$") -> float:
    """
    Parse de texto formatado como moeda para valor numérico.
    
    Args:
        texto: Texto formatado (ex: "R$ 1.234,56")
        simbolo: Símbolo da moeda (padrão: "R$")
    
    Returns:
        Valor numérico (ex: 1234.56)
    
    Examples:
        >>> parse_moeda("R$ 1.234,56")
        1234.56
        >>> parse_moeda("R$ 1000,00")
        1000.0
    """
    # Remove símbolo e espaços
    texto = texto.replace(simbolo, "").strip()
    
    # Converte separadores brasileiros para padrão
    texto = texto.replace(".", "").replace(",", ".")
    
    return float(texto)
