const { formatarCEP, limparCEP } = require('../snippet');

describe('formatarCEP', () => {
  test('CEP válido com 8 dígitos', () => {
    expect(formatarCEP('01234567')).toBe('01234-567');
  });

  test('CEP já formatado', () => {
    expect(formatarCEP('01234-567')).toBe('01234-567');
  });

  test('CEP com espaço', () => {
    expect(formatarCEP('01234 567')).toBe('01234-567');
  });

  test('CEP com tamanho inválido retorna original', () => {
    expect(formatarCEP('1234567')).toBe('1234567');
    expect(formatarCEP('123456789')).toBe('123456789');
  });
});

describe('limparCEP', () => {
  test('Remove formatação', () => {
    expect(limparCEP('01234-567')).toBe('01234567');
  });

  test('Remove espaços', () => {
    expect(limparCEP('01234 567')).toBe('01234567');
  });

  test('CEP já limpo permanece igual', () => {
    expect(limparCEP('01234567')).toBe('01234567');
  });
});
