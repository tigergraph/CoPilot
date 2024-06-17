import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { Outlet, RouterProvider, createBrowserRouter } from "react-router-dom";
import Chat from "./pages/Chat";
import ChatDialog from './pages/ChatDialog.tsx';
import { ThemeProvider } from './components/ThemeProvider.tsx';
import { ModeToggle } from '@/components/ModeToggle.tsx';

import "./components/i18n";

const Layout = () => {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <ModeToggle />
      <Outlet />
    </ThemeProvider>
  );
};

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        path: "/",
        element: <App />,
      },
      {
        path: "/chat",
        element: <Chat />,
      },
      {
        path: "/chat-dialog",
        element: <ChatDialog />,
      },
      {
        path: "/preferences",
        element: <ChatDialog />,
      }
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <RouterProvider router={router} />
);
