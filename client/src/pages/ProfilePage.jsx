import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { fetchProfile, updateProfile } from '../services/profileApi';
import ProfileAvatarUpload from '../components/ProfileAvatarUpload';
import { updateUser, logout } from '../features/auth/authSlice';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export default function ProfilePage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { id } = useParams();

  // Get current logged-in user state from Redux
  const currentUser = useSelector((state) => state.auth?.user);

  // Determine if viewing own profile or another developer's public profile
  const isOwnProfile =
    !id ||
    String(id) === String(currentUser?.id) ||
    id === currentUser?.username;

  const [profile, setProfile] = useState({
    username: '',
    email: '',
    bio: '',
    interests: '',
    profile_image: '',
  });

  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [statusMsg, setStatusMsg] = useState({ type: '', text: '' });
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  const getFullAvatarUrl = (img) => {
    if (!img || typeof img !== 'string') return null;
    if (img.startsWith('http://') || img.startsWith('https://') || img.startsWith('blob:')) {
      return img;
    }
    const cleanPath = img.replace(/^\/+/, '');
    return API_BASE_URL ? `${API_BASE_URL}/${cleanPath}` : `/${cleanPath}`;
  };

  useEffect(() => {
    const loadProfile = async () => {
      setIsLoading(true);
      try {
        // Fetch specific user profile if ID parameter exists, else fetch own profile
        const data = await fetchProfile(isOwnProfile ? undefined : id);
        const src = { ...data, ...(data?.profile || {}) };

        const fetchedProfile = {
          username: src.username || data?.username || '',
          email: src.email || data?.email || '',
          bio: src.bio || '',
          interests: src.interests || '',
          profile_image: src.profile_image || data?.profile_image || '',
        };

        setProfile(fetchedProfile);

        if (isOwnProfile) {
          dispatch(
            updateUser({
              username: fetchedProfile.username,
              email: fetchedProfile.email,
              bio: fetchedProfile.bio,
              interests: fetchedProfile.interests,
              profile_image: fetchedProfile.profile_image,
              avatar_url: fetchedProfile.profile_image,
            })
          );
        }
      } catch (err) {
        setStatusMsg({ type: 'error', text: err.message || 'Failed to load profile details.' });
      } finally {
        setIsLoading(false);
      }
    };

    loadProfile();
  }, [id, isOwnProfile, dispatch]);

  const handleAvatarUpdated = (newAvatarUrl) => {
    setProfile((prev) => ({
      ...prev,
      profile_image: newAvatarUrl,
    }));

    dispatch(
      updateUser({
        profile_image: newAvatarUrl,
        avatar_url: newAvatarUrl,
      })
    );

    setStatusMsg({ type: 'success', text: 'Profile picture updated successfully!' });
    window.dispatchEvent(new CustomEvent('user-avatar-updated', { detail: newAvatarUrl }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setStatusMsg({ type: '', text: '' });
    try {
      await updateProfile({
        bio: profile.bio,
        interests: profile.interests,
      });

      const data = await fetchProfile();
      const src = { ...data, ...(data?.profile || {}) };
      const updatedImg = src.profile_image || data?.profile_image || profile.profile_image;

      const updatedData = {
        bio: src.bio || '',
        interests: src.interests || '',
        profile_image: updatedImg,
        avatar_url: updatedImg,
      };

      setProfile((p) => ({
        ...p,
        ...updatedData,
      }));

      dispatch(updateUser(updatedData));
      setStatusMsg({ type: 'success', text: 'Profile updated successfully!' });
      setIsEditing(false);
      window.dispatchEvent(new CustomEvent('user-avatar-updated', { detail: updatedImg }));
    } catch (err) {
      setStatusMsg({ type: 'error', text: err.message });
    }
  };

  const confirmLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-gray-400 text-sm">Loading profile...</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl mx-auto py-8 px-4 relative">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
            {isOwnProfile ? 'Developer Profile' : `${profile.username || 'Developer'}'s Profile`}
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            {isOwnProfile
              ? 'Manage your account information and preferences'
              : 'Public developer details and interests'}
          </p>
        </div>

        {isOwnProfile && (
          <button
            onClick={() => setShowLogoutModal(true)}
            className="px-4 py-2 text-xs bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg transition shadow-sm cursor-pointer"
          >
            Logout
          </button>
        )}
      </div>

      {statusMsg.text && (
        <div
          className={`mb-6 p-3 rounded-lg text-xs text-center border font-medium ${
            statusMsg.type === 'error'
              ? 'bg-red-50 border-red-200 text-red-600'
              : 'bg-emerald-50 border-emerald-200 text-emerald-700'
          }`}
        >
          {statusMsg.text}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm space-y-6">
        <div className="pb-6 border-b border-gray-100">
          {isOwnProfile ? (
            <ProfileAvatarUpload user={profile} onAvatarUpdated={handleAvatarUpdated} />
          ) : (
            <div className="flex items-center gap-4">
              <div className="w-20 h-20 rounded-full overflow-hidden bg-orange-100 border-2 border-slate-200 flex items-center justify-center shadow-sm">
                {profile.profile_image ? (
                  <img
                    src={getFullAvatarUrl(profile.profile_image)}
                    alt={profile.username}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-2xl font-bold text-orange-600">
                    {profile.username?.charAt(0).toUpperCase() || 'U'}
                  </span>
                )}
              </div>
              <div>
                <h2 className="text-lg font-bold text-gray-900">{profile.username}</h2>
                <span className="inline-block text-[10px] font-mono bg-orange-50 text-orange-600 px-2 py-0.5 rounded-full mt-1 border border-orange-200/50">
                  Community Member
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-5">
          <div className={isOwnProfile ? "grid grid-cols-1 sm:grid-cols-2 gap-4" : "block"}>
            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
                Username
              </label>
              <p className="text-sm font-bold text-gray-900 break-all">{profile.username || '—'}</p>
            </div>

            {/* Email is strictly rendered ONLY for the logged-in user */}
            {isOwnProfile && (
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
                  Email
                </label>
                <p className="text-sm font-bold text-gray-900 break-all">{profile.email || '—'}</p>
              </div>
            )}
          </div>

          {isEditing && isOwnProfile ? (
            <form onSubmit={handleSave} className="space-y-4 pt-2 border-t border-gray-100">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Bio</label>
                <textarea
                  value={profile.bio}
                  onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
                  placeholder="Tell us a bit about yourself..."
                  className="w-full px-3 py-2 rounded-xl bg-gray-50 border border-gray-200 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:bg-white focus:border-orange-500 transition"
                  rows="3"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Interests</label>
                <input
                  type="text"
                  value={profile.interests}
                  onChange={(e) => setProfile({ ...profile, interests: e.target.value })}
                  placeholder="Comma-separated, e.g. DevOps, Frontend, Career"
                  className="w-full px-3 py-2 rounded-xl bg-gray-50 border border-gray-200 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:bg-white focus:border-orange-500 transition"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white font-semibold text-xs rounded-lg transition shadow-sm cursor-pointer"
                >
                  Save Changes
                </button>
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-600 text-xs font-semibold rounded-lg transition cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4 pt-4 border-t border-gray-100">
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
                  Bio
                </label>
                <p className="text-sm text-gray-700 leading-relaxed">
                  {profile.bio || 'No bio added yet.'}
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  Interests
                </label>
                {profile.interests ? (
                  <div className="flex flex-wrap gap-1.5">
                    {profile.interests
                      .split(',')
                      .map((tag) => tag.trim())
                      .filter(Boolean)
                      .map((tag) => (
                        <span
                          key={tag}
                          className="text-xs font-medium px-2.5 py-1 rounded-full bg-orange-50 text-orange-600 border border-orange-200/60"
                        >
                          {tag}
                        </span>
                      ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No interests added yet.</p>
                )}
              </div>

              {isOwnProfile && (
                <button
                  onClick={() => setIsEditing(true)}
                  className="mt-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white font-semibold text-xs rounded-lg transition shadow-sm cursor-pointer"
                >
                  Edit Profile
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {showLogoutModal && isOwnProfile && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-gray-100 text-center animate-in fade-in zoom-in duration-150">
            <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </div>
            <h3 className="text-base font-bold text-gray-900 mb-1">Confirm Sign Out</h3>
            <p className="text-xs text-gray-500 mb-6">Are you sure you want to log out of your account?</p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowLogoutModal(false)}
                className="flex-1 py-2 px-4 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold rounded-xl transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={confirmLogout}
                className="flex-1 py-2 px-4 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-xl transition shadow-sm cursor-pointer"
              >
                Log Out
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}