const { hashSenha, verificarSenha } = require('../snippet');

describe('hashSenha', () => {
  test('deve gerar hash como string', async () => {
    const hash = await hashSenha('teste123');
    expect(typeof hash).toBe('string');
  });

  test('deve começar com prefixo bcrypt', async () => {
    const hash = await hashSenha('teste123');
    expect(hash.startsWith('$2b$10$')).toBe(true);
  });

  test('deve gerar hash diferente para mesma senha', async () => {
    const hash1 = await hashSenha('teste123');
    const hash2 = await hashSenha('teste123');
    expect(hash1).not.toBe(hash2);
  });

  test('deve funcionar com rounds customizado', async () => {
    const hash = await hashSenha('teste123', 12);
    expect(hash.startsWith('$2b$12$')).toBe(true);
  });
});

describe('verificarSenha', () => {
  test('deve retornar true para senha correta', async () => {
    const hash = await hashSenha('teste123');
    const valido = await verificarSenha('teste123', hash);
    expect(valido).toBe(true);
  });

  test('deve retornar false para senha incorreta', async () => {
    const hash = await hashSenha('teste123');
    const valido = await verificarSenha('senha_errada', hash);
    expect(valido).toBe(false);
  });

  test('deve funcionar com caracteres especiais', async () => {
    const hash = await hashSenha('tëste!@#$%123');
    const valido = await verificarSenha('tëste!@#$%123', hash);
    expect(valido).toBe(true);
    
    const invalido = await verificarSenha('teste!@#$%123', hash);
    expect(invalido).toBe(false);
  });
});
