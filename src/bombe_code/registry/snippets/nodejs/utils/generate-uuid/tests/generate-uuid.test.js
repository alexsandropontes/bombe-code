const { gerarUUID, gerarUUIDSemTracos, validarUUID } = require('../snippet');

describe('gerarUUID', () => {
  test('Deve gerar UUID como string', () => {
    const resultado = gerarUUID();
    expect(typeof resultado).toBe('string');
  });

  test('Deve ter 36 caracteres', () => {
    const resultado = gerarUUID();
    expect(resultado.length).toBe(36);
  });

  test('Deve ter 4 hífens', () => {
    const resultado = gerarUUID();
    expect((resultado.match(/-/g) || []).length).toBe(4);
  });

  test('Deve gerar UUIDs únicos', () => {
    const uuid1 = gerarUUID();
    const uuid2 = gerarUUID();
    expect(uuid1).not.toBe(uuid2);
  });
});

describe('gerarUUIDSemTracos', () => {
  test('Deve ter 32 caracteres', () => {
    const resultado = gerarUUIDSemTracos();
    expect(resultado.length).toBe(32);
  });

  test('Não deve conter hífen', () => {
    const resultado = gerarUUIDSemTracos();
    expect(resultado).not.toContain('-');
  });
});

describe('validarUUID', () => {
  test('UUID válido deve retornar true', () => {
    expect(validarUUID('550e8400-e29b-41d4-a716-446655440000')).toBe(true);
  });

  test('UUID inválido deve retornar false', () => {
    expect(validarUUID('not-a-uuid')).toBe(false);
  });

  test('String vazia deve retornar false', () => {
    expect(validarUUID('')).toBe(false);
  });
});
