const { formatarMoeda, parseMoeda } = require('../snippet');

describe('formatarMoeda', () => {
  test('Valor positivo', () => {
    expect(formatarMoeda(1234.56)).toBe('R$ 1.234,56');
  });

  test('Valor inteiro', () => {
    expect(formatarMoeda(1000)).toBe('R$ 1.000,00');
  });

  test('Valor negativo', () => {
    expect(formatarMoeda(-50.5)).toBe('-R$ 50,50');
  });

  test('Símbolo customizado', () => {
    expect(formatarMoeda(1000, 'US$')).toBe('US$ 1.000,00');
  });

  test('Zero', () => {
    expect(formatarMoeda(0)).toBe('R$ 0,00');
  });

  test('Apenas centavos', () => {
    expect(formatarMoeda(0.99)).toBe('R$ 0,99');
  });
});

describe('parseMoeda', () => {
  test('Moeda completa com separadores', () => {
    expect(parseMoeda('R$ 1.234,56')).toBe(1234.56);
  });

  test('Moeda sem separador de milhar', () => {
    expect(parseMoeda('R$ 1000,00')).toBe(1000.0);
  });

  test('Símbolo customizado', () => {
    expect(parseMoeda('US$ 1.000,00', 'US$')).toBe(1000.0);
  });

  test('Moeda com espaços extras', () => {
    expect(parseMoeda('  R$ 1.000,00  ')).toBe(1000.0);
  });
});
