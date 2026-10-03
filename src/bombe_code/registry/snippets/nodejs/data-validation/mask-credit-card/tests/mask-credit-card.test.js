const { mascararCartao, validarLuhn } = require('../snippet');

describe('mascararCartao', () => {
  test('Cartão válido com 16 dígitos', () => {
    expect(mascararCartao('1234567890123456')).toBe('**** **** **** 3456');
  });

  test('Cartão com espaços', () => {
    expect(mascararCartao('1234 5678 9012 3456')).toBe('**** **** **** 3456');
  });

  test('Cartão com traços', () => {
    expect(mascararCartao('1234-5678-9012-3456')).toBe('**** **** **** 3456');
  });

  test('Mostrar apenas 2 últimos dígitos', () => {
    expect(mascararCartao('1234567890123456', 2)).toBe('**** **** **** 56');
  });

  test('Cartão com tamanho inválido retorna original', () => {
    expect(mascararCartao('123456')).toBe('123456');
  });
});

describe('validarLuhn', () => {
  test('Cartão válido pelo algoritmo de Luhn', () => {
    expect(validarLuhn('4532015112830366')).toBe(true);
  });

  test('Cartão inválido pelo algoritmo de Luhn', () => {
    expect(validarLuhn('1234567890123456')).toBe(false);
  });

  test('Cartão válido com espaços', () => {
    expect(validarLuhn('4532 0151 1283 0366')).toBe(true);
  });
});
