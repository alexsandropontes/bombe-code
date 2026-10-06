/**
 * Validador de CNPJ Brasileiro
 * Snippet oficial do Code Forge 2
 */

/**
 * Valida um CNPJ brasileiro verificando os dígitos verificadores.
 * @param {string} cnpj - CNPJ como string (pode conter pontos e traço)
 * @returns {boolean} - True se CNPJ válido, False otherwise
 * 
 * @example
 * validarCNPJ("34.028.316/0001-03") // true
 * validarCNPJ("34028316000103")     // true
 * validarCNPJ("12.345.678/0001-90") // false
 */
function validarCNPJ(cnpj) {
  // Remove caracteres não numéricos
  cnpj = cnpj.replace(/\D/g, '');
  
  // Verifica se tem 14 dígitos
  if (cnpj.length !== 14) {
    return false;
  }
  
  // Verifica se todos os dígitos são iguais
  if (/^(\d)\1{13}$/.test(cnpj)) {
    return false;
  }
  
  // Valida primeiro dígito verificador
  const pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const digito1 = calcularDigito(cnpj.slice(0, 12), pesos1);
  if (parseInt(cnpj[12]) !== digito1) {
    return false;
  }
  
  // Valida segundo dígito verificador
  const pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const digito2 = calcularDigito(cnpj.slice(0, 13), pesos2);
  return parseInt(cnpj[13]) === digito2;
}

/**
 * Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX.
 * @param {string} cnpj - CNPJ como string (apenas números)
 * @returns {string} - CNPJ formatado ou CNPJ original se inválido
 * 
 * @example
 * formatarCNPJ("34028316000103") // "34.028.316/0001-03"
 */
function formatarCNPJ(cnpj) {
  // Remove caracteres não numéricos
  cnpj = cnpj.replace(/\D/g, '');
  
  if (cnpj.length !== 14) {
    return cnpj;
  }
  
  return cnpj.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
}

/**
 * Calcula um dígito verificador do CNPJ.
 * @param {string} cnpj - CNPJ sem os dígitos verificadores
 * @param {number[]} pesos - Array de pesos
 * @returns {number} - Dígito verificador calculado
 */
function calcularDigito(cnpj, pesos) {
  let soma = 0;
  for (let i = 0; i < cnpj.length; i++) {
    soma += parseInt(cnpj[i]) * pesos[i];
  }
  const resto = soma % 11;
  return resto < 2 ? 0 : 11 - resto;
}

module.exports = { validarCNPJ, formatarCNPJ };
