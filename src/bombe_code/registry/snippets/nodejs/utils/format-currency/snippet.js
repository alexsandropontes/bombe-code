/**
 * Formatador de Moeda Brasileira (R$)
 * Snippet oficial do Code Forge 2
 */

/**
 * Formata um valor numérico como moeda brasileira.
 * @param {number} valor - Valor numérico (ex: 1234.56)
 * @param {string} simbolo - Símbolo da moeda (padrão: "R$")
 * @returns {string} - Valor formatado no padrão brasileiro (ex: "R$ 1.234,56")
 * 
 * @example
 * formatarMoeda(1234.56) // "R$ 1.234,56"
 * formatarMoeda(1000) // "R$ 1.000,00"
 * formatarMoeda(-50.5, "US$") // "-US$ 50,50"
 */
function formatarMoeda(valor, simbolo = 'R$') {
  // Formata com separadores brasileiros
  const valorFormatado = valor.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  
  return `${simbolo} ${valorFormatado}`;
}

/**
 * Parse de texto formatado como moeda para valor numérico.
 * @param {string} texto - Texto formatado (ex: "R$ 1.234,56")
 * @param {string} simbolo - Símbolo da moeda (padrão: "R$")
 * @returns {number} - Valor numérico (ex: 1234.56)
 * 
 * @example
 * parseMoeda("R$ 1.234,56") // 1234.56
 * parseMoeda("R$ 1000,00") // 1000.0
 */
function parseMoeda(texto, simbolo = 'R$') {
  // Remove símbolo e espaços
  texto = texto.replace(simbolo, '').trim();
  
  // Converte separadores brasileiros para padrão
  texto = texto.replace(/\./g, '').replace(',', '.');
  
  return parseFloat(texto);
}

module.exports = { formatarMoeda, parseMoeda };
