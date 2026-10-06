const { JwtService } = require('./jwt');
const assert = require('assert');

const jwt = new JwtService('super-secret-key-32-chars-long-123456');
const token = jwt.sign({ sub: 'user1', role: 'admin' });
const verified = jwt.verify(token);
assert(verified && verified.sub === 'user1');
assert(jwt.verify(token + 'tampered') === null);
console.log('JwtService OK');
