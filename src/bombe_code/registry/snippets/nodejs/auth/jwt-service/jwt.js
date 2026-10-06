const crypto = require('crypto');

class JwtService {
  constructor(secret, expiresInSeconds = 3600) {
    if (!secret || secret.length < 32) throw new Error('Secret deve ter pelo menos 32 caracteres.');
    this.secret = secret;
    this.expiresInSeconds = expiresInSeconds;
  }

  sign(payload) {
    const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
    const exp = Math.floor(Date.now() / 1000) + this.expiresInSeconds;
    const body = Buffer.from(JSON.stringify({ ...payload, exp })).toString('base64url');
    const data = `${header}.${body}`;
    const sig = crypto.createHmac('sha256', this.secret).update(data).digest('base64url');
    return `${data}.${sig}`;
  }

  verify(token) {
    if (!token || typeof token !== 'string') return null;
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const data = `${parts[0]}.${parts[1]}`;
    const sig = crypto.createHmac('sha256', this.secret).update(data).digest('base64url');
    
    if (!crypto.timingSafeEqual(Buffer.from(parts[2]), Buffer.from(sig))) {
      return null;
    }
    try {
      const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8'));
      if (payload.exp && Math.floor(Date.now() / 1000) > payload.exp) {
        return null;
      }
      return payload;
    } catch {
      return null;
    }
  }
}

module.exports = { JwtService };
