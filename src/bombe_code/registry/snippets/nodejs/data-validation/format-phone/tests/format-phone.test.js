const { formatarTelefone, limparTelefone } = require('../snippet');

describe('formatarTelefone', () => {
  test('Celular com 11 dígitos', () => {
    expect(formatarTelefone('11987654321')).toBe('(11) 98765-4321');
  });

  test('Celular já formatado', () => {
    expect(formatarTelefone('(11) 98765-4321')).toBe('(11) 98765-4321');
  });

  test('Fixo com 10 dígitos', () => {
    expect(formatarTelefone('1138765432')).toBe('(11) 3876-5432');
  });

  test('Fixo já formatado', () => {
    expect(formatarTelefone('(11) 3876-5432')).toBe('(11) 3876-5432');
  });

  test('Tamanho inválido retorna original', () => {
    expect(formatarTelefone('1234567')).toBe('1234567');
    expect(formatarTelefone('1234567890123')).toBe('1234567890123');
  });
});

describe('limparTelefone', () => {
  test('Remove formatação', () => {
    expect(limparTelefone('(11) 98765-4321')).toBe('11987654321');
  });

  test('Remove espaços', () => {
    expect(limparTelefone('11 98765 4321')).toBe('11987654321');
  });

  test('Telefone já limpo permanece igual', () => {
    expect(limparTelefone('11987654321')).toBe('11987654321');
  });

  test('Remove traços', () => {
    expect(limparTelefone('11-98765-4321')).toBe('11987654321');
  });
});
