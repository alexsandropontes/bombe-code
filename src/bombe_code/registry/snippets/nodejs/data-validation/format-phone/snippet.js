/**
 * Formatador de Telefone Brasileiro
 * Snippet oficial do Code Forge 2
 */

/**
 * Formata telefone no padrão (XX) XXXXX-XXXX.
 * Funciona com 10 ou 11 dígitos (com ou sem 9º dígito).
 * @param {string} telefone - Telefone como string (pode conter caracteres especiais)
 * @returns {string} - Telefone formatado ou original se inválido
 * 
 * @example
 * formatarTelefone("11987654321") // "(11) 98765-4321"
 * formatarTelefone("1138765432")  // "(11) 3876-5432"
 */
function formatarTelefone(telefone) {
  // Remove caracteres não numéricos
  telefone = limparTelefone(telefone);
  
  // Verifica tamanho e formata
  if (telefone.length === 11) {
    // Celular: (XX) XXXXX-XXXX
    return `(${telefone.slice(0, 2)}) ${telefone.slice(2, 7)}-${telefone.slice(7)}`;
  } else if (telefone.length === 10) {
    // Fixo: (XX) XXXX-XXXX
    return `(${telefone.slice(0, 2)}) ${telefone.slice(2, 6)}-${telefone.slice(6)}`;
  } else {
    // Tamanho inválido, retorna original
    return telefone;
  }
}

/**
 * Remove todos os caracteres não numéricos do telefone.
 * @param {string} telefone - Telefone como string (pode conter caracteres especiais)
 * @returns {string} - Apenas dígitos
 * 
 * @example
 * limparTelefone("(11) 98765-4321") // "11987654321"
 */
function limparTelefone(telefone) {
  return telefone.replace(/\D/g, '');
}

module.exports = { formatarTelefone, limparTelefone };
