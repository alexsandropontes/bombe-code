/**
 * Gerador de UUID v4
 * Snippet oficial do Code Forge 2
 * 
 * Instalação da dependência:
 *   npm install uuid
 */

const { v4: uuidv4 } = require('uuid');

/**
 * Gera um UUID v4 único.
 * @returns {string} - UUID como string no formato xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
 * 
 * @example
 * gerarUUID() // "550e8400-e29b-41d4-a716-446655440000"
 */
function gerarUUID() {
  return uuidv4();
}

/**
 * Gera um UUID v4 único sem traços.
 * @returns {string} - UUID como string sem traços (32 caracteres)
 * 
 * @example
 * gerarUUIDSemTracos() // "550e8400e29b41d4a716446655440000"
 */
function gerarUUIDSemTracos() {
  return uuidv4().replace(/-/g, '');
}

/**
 * Valida se uma string é um UUID válido.
 * @param {string} uuidStr - String para validar
 * @returns {boolean} - True se UUID válido, False otherwise
 * 
 * @example
 * validarUUID("550e8400-e29b-41d4-a716-446655440000") // true
 * validarUUID("not-a-uuid") // false
 */
function validarUUID(uuidStr) {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(uuidStr);
}

module.exports = { gerarUUID, gerarUUIDSemTracos, validarUUID };
