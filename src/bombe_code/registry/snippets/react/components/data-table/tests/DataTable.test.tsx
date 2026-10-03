import { render, screen } from '@testing-library/react';
import { DataTable } from './DataTable';

test('renderiza tabela vazia', () => {
  render(<DataTable columns={[{ key: 'name', header: 'Nome' }]} data={[]} />);
  expect(screen.getByText('Nenhum registro encontrado.')).toBeInTheDocument();
});
