/**
 * Formatador de CEP Brasileiro
 * Snippet oficial do Code Forge 2
 */

/**
 * Formata CEP no padrão XXXXX-XXX.
 * @param {string} cep - CEP como string (pode conter caracteres especiais)
 * @returns {string} - CEP formatado ou original se inválido
 * 
 * @example
 * formatarCEP("01234567") // "01234-567"
 * formatarCEP("01234-567") // "01234-567"
 */
function formatarCEP(cep) {
  // Remove caracteres não numéricos
  cep = limparCEP(cep);
  
  // Verifica tamanho (8 dígitos)
  if (cep.length === 8) {
    return `${cep.slice(0, 5)}-${cep.slice(5)}`;
  } else {
    // Tamanho inválido, retorna original
    return cep;
  }
}

/**
 * Remove todos os caracteres não numéricos do CEP.
 * @param {string} cep - CEP como string (pode conter caracteres especiais)
 * @returns {string} - Apenas dígitos
 * 
 * @example
 * limparCEP("01234-567") // "01234567"
 */
function limparCEP(cep) {
  return cep.replace(/\D/g, '');
}

module.exports = { formatarCEP, limparCEP };
