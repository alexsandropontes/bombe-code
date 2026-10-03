const { slugifyText } = require('../snippet');

describe('slugifyText', () => {
  test('Texto simples sem acentos', () => {
    expect(slugifyText('ola mundo')).toBe('ola-mundo');
  });

  test('Texto com acentos', () => {
    expect(slugifyText('Olá Mundo!')).toBe('ola-mundo');
    expect(slugifyText('Python é Ótimo!')).toBe('python-e-otimo');
  });

  test('Texto com caracteres especiais', () => {
    expect(slugifyText('C++ vs C#')).toBe('c-vs-c');
  });

  test('Usar separador customizado', () => {
    expect(slugifyText('Olá Mundo', '_')).toBe('ola_mundo');
  });

  test('Texto com múltiplos espaços', () => {
    expect(slugifyText('Olá    Mundo')).toBe('ola-mundo');
  });

  test('Texto já com hífens', () => {
    expect(slugifyText('ola-mundo')).toBe('ola-mundo');
  });

  test('Texto vazio retorna vazio', () => {
    expect(slugifyText('')).toBe('');
  });

  test('Texto em maiúsculas', () => {
    expect(slugifyText('OLÁ MUNDO')).toBe('ola-mundo');
  });
});
