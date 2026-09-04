import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';

import AuthLayout from './layouts/AuthLayout';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import AdminLoginPage from './pages/AdminLoginPage';
import ProtectedRoute from './components/ProtectedRoute';
import RoleRoute from './components/RoleRoute';
import AppShell from './layouts/AppShell';
import ProfilePage from './pages/ProfilePage';
import Home from './pages/Home';
import ContentDetail from './pages/ContentDetail';
import CreatePost from './pages/CreatePost';
import CreateContent from './pages/CreateContent';
import Categories from './pages/Categories';
import Notifications from './pages/Notifications';
import Wishlist from './pages/Wishlist';
import AdminDashboard from './pages/AdminDashboard';
import AiGenerator from './components/AiGenerator';

import { hydrateFromStorage } from './features/auth/authSlice';

export default function App() {
  const dispatch = useDispatch();

  // On every app load, check localStorage for a real logged-in user (once
  // the backend sets one) and load it into Redux, so the rest of the app
  // reacts to auth state instead of each page reading localStorage itself.
  useEffect(() => {
    dispatch(hydrateFromStorage());
  }, [dispatch]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public auth routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignUpPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
        </Route>

        {/* Dedicated admin sign-in — public route, intentionally separate
            from the public login form (admins are rejected there). */}
        <Route path="/admin/login" element={<AdminLoginPage />} />

        {/* Everything below requires a valid login token */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/" element={<Home />} />
            <Route path="/content/:id" element={<ContentDetail />} />
            {/* Instagram-style quick composer */}
            <Route path="/create" element={<CreatePost />} />
            {/* Long-form article editor (with AI helpers) */}
            <Route path="/create-article" element={<CreateContent />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/wishlist" element={<Wishlist />} />
            <Route path="/profile" element={<ProfilePage />} />

            {/* Admin-only: RoleRoute redirects non-admins even if they
                type the URL directly */}
            <Route element={<RoleRoute allow={['admin']} />}>
              <Route path="/admin" element={<AdminDashboard />} />
            </Route>
          </Route>
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>

      {/* Floating AI Widget */}
      <AiGenerator />
    </BrowserRouter>
  );
}