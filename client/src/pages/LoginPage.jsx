import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { loginUser } from '../services/authApi';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [adminBlocked, setAdminBlocked] = useState(false);
  const sessionExpired =
    typeof window !== 'undefined' &&
    new URLSearchParams(window.location.search).get('session') === 'expired';
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setAdminBlocked(false);

    if (!username.trim() || !password) {
      setErrorMsg('Please enter both username and password.');
      return;
    }

    setIsLoading(true);
    try {
      const data = await loginUser({ username, password });
      localStorage.setItem('token', data.token);
      // Once the backend returns user info on login (id, username, role),
      // this stores it so the rest of the app knows who's logged in.
      // Safe to keep even before that exists — data.user will just be
      // undefined and this becomes a no-op until then.
      if (data.user) {
        localStorage.setItem('user', JSON.stringify(data.user));
      }
      // Return the user to where they were (e.g. after a session-expiry
      // redirect) instead of always dumping them on the home feed.
      const next = new URLSearchParams(window.location.search).get('next');
      navigate(next && next.startsWith('/') ? next : '/');
    } catch (err) {
      const message = err.message || 'Invalid Username or Password.';
      setErrorMsg(message);
      // Admin accounts are rejected on the public form — point them to
      // the dedicated admin login instead of a dead end.
      if (err.message && err.message.toLowerCase().includes('admin')) {
        setAdminBlocked(true);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-center text-navy">Welcome Back</h2>
      <p className="text-xs text-muted text-center mt-1">Log in to Moringa Daily Dev to continue.</p>

      {errorMsg && (
        <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs text-center">
          {errorMsg}
        </div>
      )}

      {sessionExpired && !errorMsg && (
        <div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs text-center">
          Your session expired — please log in again.
        </div>
      )}

      {adminBlocked && (
        <Link
          to="/admin/login"
          className="mt-3 flex items-center justify-center gap-2 p-3 rounded-lg bg-navy-raised border border-navy-border text-cream text-xs font-semibold hover:border-brand-500/60 transition"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
          Continue on the secure admin login
        </Link>
      )}

      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <div>
          <label className="block text-xs font-medium text-navy/70 mb-1">Username</label>
          <input 
            type="text" 
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter your username"
            className="w-full px-3.5 py-2.5 rounded-lg bg-white border border-line text-sm focus:outline-none focus:border-brand-500 text-navy"
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="block text-xs font-medium text-navy/70">Password</label>
            <Link to="/forgot-password" className="text-[11px] text-brand-500 hover:underline">
              Forgot password?
            </Link>
          </div>

          <div className="relative">
            <input 
              type={showPassword ? "text" : "password"} 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3.5 py-2.5 pr-10 rounded-lg bg-white border border-line text-sm focus:outline-none focus:border-brand-500 text-navy"
            />
            
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-navy transition"
              title={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858-5.908a10.02 10.02 0 013.682-.863c4.478 0 8.268 2.943 9.542 7a10.025 10.025 0 01-4.132 5.411m-2.527 2.527L3 3l18 18" /></svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
              )}
            </button>
          </div>
        </div>

        <button 
          type="submit" 
          disabled={isLoading}
          className="w-full py-2.5 bg-brand-500 hover:bg-brand-600 text-white font-semibold rounded-lg transition duration-200 disabled:opacity-50"
        >
          {isLoading ? 'Logging in...' : 'Login'}
        </button>
      </form>

      <p className="text-xs text-center text-muted mt-6">
        Don't have an account?{' '}
        <Link to="/signup" className="text-brand-500 font-semibold hover:underline">
          Sign up
        </Link>
      </p>

      <p className="text-[11px] text-center text-muted/70 mt-3">
        Admin?{' '}
        <Link to="/admin/login" className="text-navy/60 hover:text-navy font-medium underline underline-offset-2">
          Sign in on the admin portal
        </Link>
      </p>
    </div>
  );
}
