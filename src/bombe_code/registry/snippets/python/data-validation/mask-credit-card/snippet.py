"""
Mascara de Cartão de Crédito
Snippet oficial do Code Forge 2
"""


def mascarar_cartao(cartao: str, mostrar_ultimos: int = 4) -> str:
    """
    Mascara número de cartão de crédito, mostrando apenas os últimos dígitos.
    
    Args:
        cartao: Número do cartão (pode conter espaços ou traços)
        mostrar_ultimos: Quantos dígitos mostrar no final (padrão: 4)
    
    Returns:
        Cartão mascarado no formato **** **** **** 1234
    
    Examples:
        >>> mascarar_cartao("1234567890123456")
        '**** **** **** 3456'
        >>> mascarar_cartao("1234567890123456", mostrar_ultimos=2)
        '**** **** **** 56'
    """
    # Remove caracteres não numéricos
    cartao = ''.join(filter(str.isdigit, cartao))
    
    # Verifica tamanho (13-19 dígitos é o padrão de cartões)
    if len(cartao) < 13 or len(cartao) > 19:
        return cartao
    
    # Calcula quantos dígitos mascarar
    total_mascarar = len(cartao) - mostrar_ultimos
    
    # Cria a parte mascarada
    mascarado = '*' * total_mascarar
    
    # Pega os últimos dígitos
    ultimos = cartao[-mostrar_ultimos:]
    
    # Junta e formata em grupos de 4
    completo = mascarado + ultimos
    
    # Formata em grupos de 4
    grupos = [completo[i:i+4] for i in range(0, len(completo), 4)]
    
    return ' '.join(grupos)


def validar_luhn(cartao: str) -> bool:
    """
    Valida número de cartão usando algoritmo de Luhn.
    
    Args:
        cartao: Número do cartão
    
    Returns:
        True se cartão válido pelo algoritmo de Luhn, False otherwise
    
    Examples:
        >>> validar_luhn("4532015112830366")
        True
        >>> validar_luhn("1234567890123456")
        False
    """
    # Remove caracteres não numéricos
    cartao = ''.join(filter(str.isdigit, cartao))
    
    # Inverte os dígitos
    digitos = [int(d) for d in cartao][::-1]
    
    # Aplica algoritmo de Luhn
    soma = 0
    for i, digito in enumerate(digitos):
        if i % 2 == 1:
            digito *= 2
            if digito > 9:
                digito -= 9
        soma += digito
    
    return soma % 10 == 0
