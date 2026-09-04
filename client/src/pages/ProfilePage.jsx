import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchProfile, updateProfile } from '../services/profileApi';

export default function ProfilePage() {
  const [profile, setProfile] = useState({
    username: '',
    email: '',
    bio: '',
    skills: '',
    github_url: '',
    interests: '',
  });
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [statusMsg, setStatusMsg] = useState({ type: '', text: '' });
  const navigate = useNavigate();

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const data = await fetchProfile();
        // Support both the flat response and a nested { profile: {... } } one
        const src = { ...data, ...(data?.profile || {}) };
        setProfile({
          username: src.username || '',
          email: src.email || '',
          bio: src.bio || '',
          skills: src.skills || '',
          github_url: src.github_url || src.github_profile || '',
          interests: src.interests || '',
        });
      } catch (err) {
        setStatusMsg({ type: 'error', text: err.message });
      } finally {
        setIsLoading(false);
      }
    };

    loadProfile();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setStatusMsg({ type: '', text: '' });
    try {
      await updateProfile({
        bio: profile.bio,
        skills: profile.skills,
        github_url: profile.github_url,
        interests: profile.interests,
      });
      // Re-read from the server so what you see is exactly what was saved
      // (skills & GitHub URL used to "disappear" after a reload because the
      // saved state never round-tripped).
      const data = await fetchProfile();
      const src = { ...data, ...(data?.profile || {}) };
      setProfile((p) => ({
        ...p,
        bio: src.bio || '',
        skills: src.skills || '',
        github_url: src.github_url || src.github_profile || '',
        interests: src.interests || '',
      }));
      setStatusMsg({ type: 'success', text: 'Profile updated successfully!' });
      setIsEditing(false);
    } catch (err) {
      setStatusMsg({ type: 'error', text: err.message });
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-muted text-sm">Loading profile...</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="max-w-2xl">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-brand-500">Developer Profile</h1>
          <button
            onClick={handleLogout}
            className="px-3.5 py-1.5 text-xs bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg transition"
          >
            Logout
          </button>
        </div>

        {statusMsg.text && (
          <div
            className={`mb-4 p-3 rounded-lg text-xs text-center border ${
              statusMsg.type === 'error'
                ? 'bg-red-500/10 border-red-500/20 text-red-400'
                : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
            }`}
          >
            {statusMsg.text}
          </div>
        )}

        <div className="bg-surface border border-line rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-xs text-muted">Username</label>
            <p className="text-base font-semibold text-navy">{profile.username}</p>
          </div>

          <div>
            <label className="block text-xs text-muted">Email</label>
            <p className="text-base font-semibold text-navy">{profile.email}</p>
          </div>

          {isEditing ? (
            <form onSubmit={handleSave} className="space-y-4 pt-2">
              <div>
                <label className="block text-xs text-navy/70 mb-1">Bio</label>
                <textarea
                  value={profile.bio}
                  onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-white border border-line text-sm text-navy focus:outline-none focus:border-brand-500"
                  rows="3"
                />
              </div>

              <div>
                <label className="block text-xs text-navy/70 mb-1">Skills / Tech Stack</label>
                <input
                  type="text"
                  value={profile.skills}
                  onChange={(e) => setProfile({ ...profile, skills: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-white border border-line text-sm text-navy focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs text-navy/70 mb-1">GitHub Profile URL</label>
                <input
                  type="url"
                  value={profile.github_url}
                  onChange={(e) => setProfile({ ...profile, github_url: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-white border border-line text-sm text-navy focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs text-navy/70 mb-1">Interests</label>
                <input
                  type="text"
                  value={profile.interests}
                  onChange={(e) => setProfile({ ...profile, interests: e.target.value })}
                  placeholder="Comma-separated, e.g. DevOps, Frontend, Career"
                  className="w-full px-3 py-2 rounded-lg bg-white border border-line text-sm text-navy focus:outline-none focus:border-brand-500"
                />
                <p className="text-[11px] text-muted mt-1">
                  Used to personalize your recommended feed and subscription suggestions.
                </p>
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white font-semibold text-xs rounded-lg transition"
                >
                  Save Changes
                </button>
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="px-4 py-2 bg-surface hover:bg-line/60 text-navy/70 text-xs rounded-lg transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4 pt-2 border-t border-line">
              <div>
                <label className="block text-xs text-muted">Bio</label>
                <p className="text-sm text-navy/70">{profile.bio || 'No bio added yet.'}</p>
              </div>

              <div>
                <label className="block text-xs text-muted">Skills</label>
                <p className="text-sm text-navy/70">{profile.skills || 'No skills listed yet.'}</p>
              </div>

              <div>
                <label className="block text-xs text-muted">GitHub</label>
                {profile.github_url ? (
                  <a
                    href={profile.github_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-brand-500 hover:underline"
                  >
                    {profile.github_url}
                  </a>
                ) : (
                  <p className="text-sm text-navy/70">Not provided</p>
                )}
              </div>

              <div>
                <label className="block text-xs text-muted mb-1.5">Interests</label>
                {profile.interests ? (
                  <div className="flex flex-wrap gap-1.5">
                    {profile.interests.split(',').map((tag) => tag.trim()).filter(Boolean).map((tag) => (
                      <span
                        key={tag}
                        className="text-[11px] font-mono px-2 py-1 rounded-full bg-surface text-navy/70 border border-line"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-navy/70">No interests added yet.</p>
                )}
              </div>

              <button
                onClick={() => setIsEditing(true)}
                className="mt-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white font-semibold text-xs rounded-lg transition"
              >
                Edit Profile
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
