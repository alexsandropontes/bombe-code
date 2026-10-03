/**
 * Validador de Formato de Email
 * Snippet oficial do Code Forge 2
 */

/**
 * Valida formato de email conforme RFC 5322.
 * @param {string} email - Email como string
 * @returns {boolean} - True se email válido, False otherwise
 * 
 * @example
 * validarEmail("usuario@exemplo.com") // true
 * validarEmail("email-invalido") // false
 */
function validarEmail(email) {
  // Padrão RFC 5322 simplificado (cobre 99% dos casos reais)
  const padrao = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return padrao.test(email);
}

/**
 * Normaliza email para lowercase.
 * @param {string} email - Email como string
 * @returns {string} - Email em lowercase
 * 
 * @example
 * normalizarEmail("Usuario@EXEMPLO.com") // "usuario@exemplo.com"
 */
function normalizarEmail(email) {
  return email.toLowerCase().trim();
}

module.exports = { validarEmail, normalizarEmail };
