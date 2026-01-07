import { createHashRouter, Navigate } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { PapersPage } from '@/pages/PapersPage';
import { NewsPage } from '@/pages/NewsPage';
import { ReportsPage } from '@/pages/ReportsPage';

export const router = createHashRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/reports" replace /> },
      { path: "papers", element: <PapersPage /> },
      { path: "news", element: <NewsPage /> },
      { path: "reports", element: <ReportsPage /> },
    ],
  },
]);

