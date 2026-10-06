const { validarEmail, normalizarEmail } = require('../snippet');

describe('validarEmail', () => {
  test('Email válido', () => {
    expect(validarEmail('usuario@exemplo.com')).toBe(true);
  });

  test('Email com ponto', () => {
    expect(validarEmail('usuario.nome@exemplo.com')).toBe(true);
  });

  test('Email com +', () => {
    expect(validarEmail('usuario+tag@exemplo.com')).toBe(true);
  });

  test('Email com sublinhado', () => {
    expect(validarEmail('usuario_nome@exemplo.com')).toBe(true);
  });

  test('Email sem @ é inválido', () => {
    expect(validarEmail('email-invalido')).toBe(false);
  });

  test('Email sem domínio é inválido', () => {
    expect(validarEmail('usuario@')).toBe(false);
  });

  test('Email sem TLD é inválido', () => {
    expect(validarEmail('usuario@exemplo')).toBe(false);
  });

  test('Email com espaço é inválido', () => {
    expect(validarEmail('usuario @exemplo.com')).toBe(false);
  });
});

describe('normalizarEmail', () => {
  test('Converte para lowercase', () => {
    expect(normalizarEmail('Usuario@EXEMPLO.com')).toBe('usuario@exemplo.com');
  });

  test('Remove espaços', () => {
    expect(normalizarEmail('  usuario@exemplo.com  ')).toBe('usuario@exemplo.com');
  });

  test('Email já em lowercase permanece igual', () => {
    expect(normalizarEmail('usuario@exemplo.com')).toBe('usuario@exemplo.com');
  });
});
