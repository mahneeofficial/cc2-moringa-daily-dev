import { useState } from 'react';
import { Link } from 'react-router-dom';
import { requestPasswordReset } from '../services/authApi';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [statusMsg, setStatusMsg] = useState('');
  const [devLink, setDevLink] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!email.trim()) return;
    setError('');
    setStatusMsg('');
    setDevLink('');
    setIsLoading(true);
    try {
      const data = await requestPasswordReset(email.trim());
      // Deliberately generic wording — don't confirm/deny whether this
      // email has an account, which is standard practice for this flow.
      setStatusMsg(`If an account exists for ${email}, a reset link has been sent.`);
      // Dev-only: when SMTP isn't configured the backend (in DEBUG mode)
      // returns the reset link directly so the flow is still testable.
      if (data?.dev_reset_url) {
        setStatusMsg('Email sending is not configured on this server (development mode). Use the link below to reset your password:');
        setDevLink(data.dev_reset_url);
      }
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-center text-navy">Reset Password</h2>
      <p className="text-xs text-muted text-center mt-1">Enter your registered email to receive instructions.</p>

      {statusMsg && (
        <div className="mt-4 p-3 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-600 text-xs text-center">
          {statusMsg}
        </div>
      )}
      {devLink && (
        <div className="mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-center break-all">
          <a href={devLink} className="text-brand-500 font-semibold hover:underline">
            Open password reset link →
          </a>
        </div>
      )}
      {error && (
        <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs text-center">
          {error}
        </div>
      )}

      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <div>
          <label className="block text-xs font-medium text-navy/70 mb-1">Email address</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="student@moringa.com"
            className="w-full px-3.5 py-2.5 rounded-lg bg-white border border-line text-sm focus:outline-none focus:border-brand-500 text-navy"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-2.5 bg-brand-500 hover:bg-brand-600 text-white font-semibold rounded-lg transition duration-200 disabled:opacity-50"
        >
          {isLoading ? 'Sending…' : 'Send Reset Link'}
        </button>
      </form>

      <p className="text-xs text-center text-muted mt-6">
        <Link to="/login" className="text-brand-500 font-semibold hover:underline">
          ← Back to Login
        </Link>
      </p>
    </div>
  );
}

