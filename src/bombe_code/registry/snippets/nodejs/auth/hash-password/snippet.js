/**
 * Hash de Senha com Bcrypt
 * Snippet oficial do Code Forge 2
 * 
 * Instalação da dependência:
 *   npm install bcrypt
 */

const bcrypt = require('bcrypt');

/**
 * Gera hash de senha usando bcrypt com salt automático.
 * @param {string} senha - Senha em texto claro
 * @param {number} rounds - Custo do bcrypt (padrão: 10)
 * @returns {Promise<string>} - Hash da senha (inclui salt)
 * 
 * @example
 * const hash = await hashSenha("minha_senha_forte");
 * console.log(hash.startsWith('$2b$10$')); // true
 */
async function hashSenha(senha, rounds = 10) {
  const salt = await bcrypt.genSalt(rounds);
  const hash = await bcrypt.hash(senha, salt);
  return hash;
}

/**
 * Verifica se uma senha corresponde ao hash.
 * @param {string} senha - Senha em texto claro
 * @param {string} hash - Hash da senha (gerado por hashSenha)
 * @returns {Promise<boolean>} - True se a senha corresponde, False otherwise
 * 
 * @example
 * const hash = await hashSenha("minha_senha");
 * const valido = await verificarSenha("minha_senha", hash);
 * console.log(valido); // true
 */
async function verificarSenha(senha, hash) {
  return bcrypt.compare(senha, hash);
}

module.exports = { hashSenha, verificarSenha };
