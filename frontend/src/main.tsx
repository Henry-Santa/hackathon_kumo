import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider, Outlet } from 'react-router-dom';
import Topbar from './components/Topbar';
import SignIn from './pages/SignIn';
import SignUp from './pages/SignUp';
import UniversityProfile from './pages/UniversityProfile';
import ProfilePage from './pages/Profile';
import SearchPage from './pages/Search';

function Layout() {
  return (
    <div>
      <Topbar />
      <Outlet />
    </div>
  );
}

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <SignIn /> },
      { path: '/signup', element: <SignUp /> },
      { path: '/profile', element: <UniversityProfile /> },
      { path: '/account', element: <ProfilePage /> },
      { path: '/search', element: <SearchPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);


