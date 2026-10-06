"""
Validador de CPF Brasileiro
Snippet oficial do Code Forge 2
"""


def validar_cpf(cpf: str) -> bool:
    """
    Valida CPF brasileiro removendo caracteres não numéricos e verificando dígitos.
    
    Args:
        cpf: CPF como string (pode conter pontos e traço)
    
    Returns:
        True se CPF válido, False otherwise
    
    Examples:
        >>> validar_cpf("123.456.789-09")
        False
        >>> validar_cpf("52998224725")
        True
    """
    # Remove caracteres não numéricos
    cpf = ''.join(filter(str.isdigit, cpf))
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais (ex: 111.111.111-11)
    if len(set(cpf)) == 1:
        return False
    
    # Valida primeiro dígito verificador
    soma = sum(int(digito) * (10 - i) for i, digito in enumerate(cpf[:9]))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if int(cpf[9]) != digito1:
        return False
    
    # Valida segundo dígito verificador
    soma = sum(int(digito) * (11 - i) for i, digito in enumerate(cpf[:10]))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    return int(cpf[10]) == digito2


def formatar_cpf(cpf: str) -> str:
    """
    Formata CPF no padrão XXX.XXX.XXX-XX.
    
    Args:
        cpf: CPF como string (apenas números)
    
    Returns:
        CPF formatado ou CPF original se inválido
    
    Examples:
        >>> formatar_cpf("12345678909")
        '123.456.789-09'
    """
    cpf = ''.join(filter(str.isdigit, cpf))
    
    if len(cpf) != 11:
        return cpf
    
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
