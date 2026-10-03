/**
 * Slugify - Conversor de Texto para Slug
 * Snippet oficial do Code Forge 2
 * 
 * Instalação da dependência:
 *   npm install slugify
 */

const slugify = require('slugify');

/**
 * Converte texto em slug para URLs.
 * @param {string} texto - Texto original
 * @param {string} separador - Separador a ser usado (padrão: '-')
 * @returns {string} - Texto convertido em slug (lowercase, sem acentos, apenas alphanumeric)
 * 
 * @example
 * slugify("Olá Mundo!") // "ola-mundo"
 * slugify("Python é Ótimo!") // "python-e-otimo"
 * slugify("Hello World", "_") // "hello_world"
 */
function slugifyText(texto, separador = '-') {
  return slugify(texto, {
    lower: true,
    strict: true,
    replacement: separador,
  });
}

module.exports = { slugifyText };
