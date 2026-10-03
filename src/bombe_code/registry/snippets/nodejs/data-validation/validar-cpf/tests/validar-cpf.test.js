const { validarCPF, formatarCPF } = require('../snippet');

describe('validarCPF', () => {
  test('CPF válido com formatação', () => {
    expect(validarCPF('529.982.247-25')).toBe(true);
  });

  test('CPF válido sem formatação', () => {
    expect(validarCPF('52998224725')).toBe(true);
  });

  test('CPF inválido', () => {
    expect(validarCPF('123.456.789-09')).toBe(false);
  });

  test('CPF com todos dígitos iguais', () => {
    expect(validarCPF('111.111.111-11')).toBe(false);
    expect(validarCPF('00000000000')).toBe(false);
  });

  test('CPF com tamanho inválido', () => {
    expect(validarCPF('123.456.789')).toBe(false);
    expect(validarCPF('1234567890123')).toBe(false);
  });

  test('CPF com caracteres especiais', () => {
    expect(validarCPF('529.982-247-25')).toBe(true);
  });
});

describe('formatarCPF', () => {
  test('Formata CPF válido', () => {
    expect(formatarCPF('52998224725')).toBe('529.982.247-25');
  });

  test('CPF já formatado permanece igual', () => {
    expect(formatarCPF('529.982.247-25')).toBe('529.982.247-25');
  });

  test('CPF inválido retorna original', () => {
    expect(formatarCPF('123456789')).toBe('123456789');
  });
});
