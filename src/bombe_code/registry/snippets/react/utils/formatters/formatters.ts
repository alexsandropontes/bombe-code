export function formatCpf(val: string | null | undefined): string {
  if (!val) return '';
  const clean = val.replace(/\D/g, '');
  if (clean.length !== 11) return val;
  return clean.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
}

export function formatCnpj(val: string | null | undefined): string {
  if (!val) return '';
  const clean = val.replace(/\D/g, '');
  if (clean.length !== 14) return val;
  return clean.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
}

export function formatCurrencyBrl(val: number | null | undefined): string {
  if (val == null) return 'R$ 0,00';
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
}

export function formatPhoneBr(val: string | null | undefined): string {
  if (!val) return '';
  const clean = val.replace(/\D/g, '');
  if (clean.length === 11) {
    return clean.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
  } else if (clean.length === 10) {
    return clean.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
  }
  return val;
}
