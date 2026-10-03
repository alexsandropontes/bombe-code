const { validarCNPJ, formatarCNPJ } = require('../snippet');

describe('validarCNPJ', () => {
  test('CNPJ válido com formatação', () => {
    expect(validarCNPJ('34.028.316/0001-03')).toBe(true);
  });

  test('CNPJ válido sem formatação', () => {
    expect(validarCNPJ('34028316000103')).toBe(true);
  });

  test('CNPJ inválido', () => {
    expect(validarCNPJ('12.345.678/0001-90')).toBe(false);
  });

  test('CNPJ com todos dígitos iguais', () => {
    expect(validarCNPJ('11111111111111')).toBe(false);
  });

  test('CNPJ com tamanho inválido', () => {
    expect(validarCNPJ('340283160001')).toBe(false);
  });
});

describe('formatarCNPJ', () => {
  test('Formata CNPJ válido', () => {
    expect(formatarCNPJ('34028316000103')).toBe('34.028.316/0001-03');
  });

  test('CNPJ já formatado permanece igual', () => {
    expect(formatarCNPJ('34.028.316/0001-03')).toBe('34.028.316/0001-03');
  });

  test('CNPJ inválido retorna original', () => {
    expect(formatarCNPJ('34028316')).toBe('34028316');
  });
});
