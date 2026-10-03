/**
 * Validador de CPF Brasileiro
 * Snippet oficial do Code Forge 2
 */

/**
 * Valida um CPF brasileiro verificando os dígitos verificadores.
 * @param {string} cpf - CPF como string (pode conter pontos e traço)
 * @returns {boolean} - True se CPF válido, False otherwise
 * 
 * @example
 * validarCPF("529.982.247-25") // true
 * validarCPF("52998224725")    // true
 * validarCPF("123.456.789-09") // false
 */
function validarCPF(cpf) {
  // Remove caracteres não numéricos
  cpf = cpf.replace(/\D/g, '');
  
  // Verifica se tem 11 dígitos
  if (cpf.length !== 11) {
    return false;
  }
  
  // Verifica se todos os dígitos são iguais
  if (/^(\d)\1{10}$/.test(cpf)) {
    return false;
  }
  
  // Valida primeiro dígito verificador
  const digito1 = calcularDigito(cpf.slice(0, 9), 10);
  if (parseInt(cpf[9]) !== digito1) {
    return false;
  }
  
  // Valida segundo dígito verificador
  const digito2 = calcularDigito(cpf.slice(0, 10), 11);
  return parseInt(cpf[10]) === digito2;
}

/**
 * Formata CPF no padrão XXX.XXX.XXX-XX.
 * @param {string} cpf - CPF como string (apenas números)
 * @returns {string} - CPF formatado ou CPF original se inválido
 * 
 * @example
 * formatarCPF("52998224725") // "529.982.247-25"
 */
function formatarCPF(cpf) {
  // Remove caracteres não numéricos
  cpf = cpf.replace(/\D/g, '');
  
  if (cpf.length !== 11) {
    return cpf;
  }
  
  return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
}

/**
 * Calcula um dígito verificador do CPF.
 * @param {string} cpf - CPF sem os dígitos verificadores
 * @param {number} weights - Peso inicial (10 para primeiro dígito, 11 para o segundo)
 * @returns {number} - Dígito verificador calculado
 */
function calcularDigito(cpf, weights) {
  let soma = 0;
  for (let i = 0; i < cpf.length; i++) {
    soma += parseInt(cpf[i]) * (weights - i);
  }
  const resto = soma % 11;
  return resto < 2 ? 0 : 11 - resto;
}

module.exports = { validarCPF, formatarCPF };
