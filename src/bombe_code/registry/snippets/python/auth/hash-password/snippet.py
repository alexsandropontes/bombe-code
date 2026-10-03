"""
Hash de Senha com Bcrypt
Snippet oficial do Code Forge 2

Instalação da dependência:
    pip install bcrypt
"""
import bcrypt


def hash_senha(senha: str, rounds: int = 12) -> str:
    """
    Gera hash de senha usando bcrypt com salt automático.
    
    Args:
        senha: Senha em texto claro
        rounds: Custo do bcrypt (padrão: 12)
    
    Returns:
        Hash da senha como string (inclui salt)
    
    Examples:
        >>> hash = hash_senha("minha_senha_forte")
        >>> hash.startswith('$2b$12$')
        True
    """
    # Codifica a senha para bytes
    senha_bytes = senha.encode('utf-8')
    
    # Gera salt e hash
    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(senha_bytes, salt)
    
    return hashed.decode('utf-8')


def verificar_senha(senha: str, hash: str) -> bool:
    """
    Verifica se uma senha corresponde ao hash.
    
    Args:
        senha: Senha em texto claro
        hash: Hash da senha (gerado por hash_senha)
    
    Returns:
        True se a senha corresponde, False otherwise
    
    Examples:
        >>> hash = hash_senha("minha_senha")
        >>> verificar_senha("minha_senha", hash)
        True
        >>> verificar_senha("senha_errada", hash)
        False
    """
    senha_bytes = senha.encode('utf-8')
    hash_bytes = hash.encode('utf-8')
    
    return bcrypt.checkpw(senha_bytes, hash_bytes)
