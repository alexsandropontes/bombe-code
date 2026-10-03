import { formatCpf, formatCurrencyBrl } from './formatters';
test('formata cpf', () => {
  expect(formatCpf('52998224725')).toBe('529.982.247-25');
  expect(formatCurrencyBrl(10.5)).toContain('10,50');
});
