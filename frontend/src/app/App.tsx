import { BrowserRouter } from 'react-router-dom';
import { DataProvider } from '@/app/DataProvider';
import { AppRoutes } from '@/app/routes';

export function App() {
  return (
    <BrowserRouter>
      <DataProvider>
        <AppRoutes />
      </DataProvider>
    </BrowserRouter>
  );
}
