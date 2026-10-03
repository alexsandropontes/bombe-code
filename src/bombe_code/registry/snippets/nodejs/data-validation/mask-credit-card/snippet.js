/**
 * Máscara de Cartão de Crédito
 * Snippet oficial do Code Forge 2
 */

/**
 * Mascara número de cartão de crédito, mostrando apenas os últimos dígitos.
 * @param {string} cartao - Número do cartão (pode conter espaços ou traços)
 * @param {number} mostrarUltimos - Quantos dígitos mostrar no final (padrão: 4)
 * @returns {string} - Cartão mascarado no formato **** **** **** 1234
 * 
 * @example
 * mascararCartao("1234567890123456") // "**** **** **** 3456"
 * mascararCartao("1234567890123456", 2) // "**** **** **** 56"
 */
function mascararCartao(cartao, mostrarUltimos = 4) {
  // Remove caracteres não numéricos
  cartao = limparCartao(cartao);
  
  // Verifica tamanho (13-19 dígitos é o padrão de cartões)
  if (cartao.length < 13 || cartao.length > 19) {
    return cartao;
  }
  
  // Calcula quantos dígitos mascarar
  const totalMascarar = cartao.length - mostrarUltimos;
  
  // Cria a parte mascarada
  const mascarado = '*'.repeat(totalMascarar);
  
  // Pega os últimos dígitos
  const ultimos = cartao.slice(-mostrarUltimos);
  
  // Junta e formata em grupos de 4
  const completo = mascarado + ultimos;
  
  // Formata em grupos de 4
  const grupos = completo.match(/.{1,4}/g) || [];
  
  return grupos.join(' ');
}

/**
 * Valida número de cartão usando algoritmo de Luhn.
 * @param {string} cartao - Número do cartão
 * @returns {boolean} - True se cartão válido pelo algoritmo de Luhn, False otherwise
 * 
 * @example
 * validarLuhn("4532015112830366") // true
 * validarLuhn("1234567890123456") // false
 */
function validarLuhn(cartao) {
  // Remove caracteres não numéricos
  cartao = limparCartao(cartao);
  
  // Inverte os dígitos
  const digitos = cartao.split('').reverse().map(Number);
  
  // Aplica algoritmo de Luhn
  let soma = 0;
  for (let i = 0; i < digitos.length; i++) {
    let digito = digitos[i];
    if (i % 2 === 1) {
      digito *= 2;
      if (digito > 9) {
        digito -= 9;
      }
    }
    soma += digito;
  }
  
  return soma % 10 === 0;
}

/**
 * Remove todos os caracteres não numéricos do cartão.
 * @param {string} cartao - Número do cartão
 * @returns {string} - Apenas dígitos
 */
function limparCartao(cartao) {
  return cartao.replace(/\D/g, '');
}

module.exports = { mascararCartao, validarLuhn, limparCartao };
