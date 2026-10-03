"""
Validador de CNPJ Brasileiro
Snippet oficial do Code Forge 2
"""


def validar_cnpj(cnpj: str) -> bool:
    """
    Valida CNPJ brasileiro removendo caracteres não numéricos e verificando dígitos.
    
    Args:
        cnpj: CNPJ como string (pode conter pontos e traço)
    
    Returns:
        True se CNPJ válido, False otherwise
    
    Examples:
        >>> validar_cnpj("34.028.316/0001-03")
        True
        >>> validar_cnpj("12.345.678/0001-90")
        False
    """
    # Remove caracteres não numéricos
    cnpj = ''.join(filter(str.isdigit, cnpj))
    
    # Verifica se tem 14 dígitos
    if len(cnpj) != 14:
        return False
    
    # Verifica se todos os dígitos são iguais
    if len(set(cnpj)) == 1:
        return False
    
    # Valida primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(digito) * peso for digito, peso in zip(cnpj[:12], pesos1))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if int(cnpj[12]) != digito1:
        return False
    
    # Valida segundo dígito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(digito) * peso for digito, peso in zip(cnpj[:13], pesos2))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    return int(cnpj[13]) == digito2


def formatar_cnpj(cnpj: str) -> str:
    """
    Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX.
    
    Args:
        cnpj: CNPJ como string (apenas números)
    
    Returns:
        CNPJ formatado ou CNPJ original se inválido
    
    Examples:
        >>> formatar_cnpj("34028316000103")
        '34.028.316/0001-03'
    """
    cnpj = ''.join(filter(str.isdigit, cnpj))
    
    if len(cnpj) != 14:
        return cnpj
    
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
