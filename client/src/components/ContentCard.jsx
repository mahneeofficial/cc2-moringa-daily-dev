import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  Heart, 
  Bookmark, 
  Eye, 
  MessageSquare, 
  LogIn, 
  X, 
  Music, 
  Image as ImageIcon,
  Play,
  Pause,
  Volume2,
  VolumeX
} from 'lucide-react';
import { toggleWishlist } from '../../services/wishlistApi';
import apiRequest from '../../services/api';

export default function ContentCard({ post, item, content, onUpdate }) {
  const navigate = useNavigate();

  // Safely extract post payload regardless of prop name used (post, item, or content)
  const rawTarget = post || item || content;

  const currentPost = (() => {
    if (!rawTarget || typeof rawTarget !== 'object') return null;

    // Check if wrapped in a pivot object with null/deleted content
    if ('content' in rawTarget && !rawTarget.content) return null;
    if ('Content' in rawTarget && !rawTarget.Content) return null;

    if (rawTarget.content && typeof rawTarget.content === 'object') return rawTarget.content;
    if (rawTarget.Content && typeof rawTarget.Content === 'object') return rawTarget.Content;
    if (rawTarget.post && typeof rawTarget.post === 'object') return rawTarget.post;

    return rawTarget;
  })();

  // Hooks run unconditionally at the top level
  const [liked, setLiked] = useState(() => Boolean(currentPost?.is_liked || currentPost?.isLiked));
  const [bookmarked, setBookmarked] = useState(() => Boolean(currentPost?.is_bookmarked || currentPost?.isBookmarked || rawTarget?.is_bookmarked));
  const [likesCount, setLikesCount] = useState(() => Number(currentPost?.likes_count || currentPost?.LikesCount || 0));
  const [showAuthModal, setShowAuthModal] = useState(false);

  // Hover Media State
  const [isHovered, setIsHovered] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const videoRef = useRef(null);
  const audioRef = useRef(null);

  useEffect(() => {
    setLiked(Boolean(currentPost?.is_liked || currentPost?.isLiked));
    setBookmarked(Boolean(currentPost?.is_bookmarked || currentPost?.isBookmarked || rawTarget?.is_bookmarked));
    setLikesCount(Number(currentPost?.likes_count || currentPost?.LikesCount || 0));
  }, [post, item, content, currentPost, rawTarget]);

  // Handle Video Hover Auto-Preview
  useEffect(() => {
    if (!videoRef.current) return;

    if (isHovered) {
      const playPromise = videoRef.current.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => setIsPlaying(true))
          .catch(() => setIsPlaying(false));
      }
    } else {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
      setIsPlaying(false);
    }
  }, [isHovered]);

  // Skip rendering if payload is missing or invalid
  if (!rawTarget || typeof rawTarget !== 'object' || !currentPost) {
    return null;
  }

  const rawType = currentPost?.content_type || currentPost?.type || currentPost?.Type || 'article';
  const contentType = String(rawType).toLowerCase();
  const mediaUrl = currentPost?.media_url || currentPost?.content_url || currentPost?.url || currentPost?.file_path;
  const thumbnailUrl = currentPost?.thumbnail_url || currentPost?.thumbnail;
  const postId = currentPost?.id || currentPost?.content_id || currentPost?.ContentID || rawTarget?.id;

  const authorId = currentPost?.author?.id || currentPost?.author_id || currentPost?.user_id || currentPost?.user?.id || currentPost?.UserID;
  const authorName = currentPost?.author?.username || currentPost?.author_name || currentPost?.user?.username;

  const handleCardClick = () => {
    if (postId) navigate(`/content/${postId}`);
  };

  const handleLike = async (e) => {
    e.stopPropagation();
    if (!postId) return;

    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    if (!token) {
      setShowAuthModal(true);
      return;
    }

    const nextLiked = !liked;
    try {
      const updated = await apiRequest(`/api/posts/${postId}/like`, {
        method: 'PATCH',
        body: { liked: nextLiked }
      });

      const newLiked = updated?.is_liked ?? nextLiked;
      const newCount = Number(updated?.likes_count ?? likesCount);

      setLiked(newLiked);
      setLikesCount(newCount);
      if (onUpdate) onUpdate({ ...currentPost, is_liked: newLiked, likes_count: newCount });
    } catch (error) {
      console.error("Error updating like:", error);
    }
  };

  const handleBookmark = async (e) => {
    e.stopPropagation();
    if (!postId) return;

    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    if (!token) {
      setShowAuthModal(true);
      return;
    }

    const nextBookmarked = !bookmarked;
    setBookmarked(nextBookmarked);

    try {
      await toggleWishlist(postId, bookmarked);
      if (onUpdate) onUpdate({ ...currentPost, is_bookmarked: nextBookmarked });
    } catch (error) {
      console.error("Error toggling bookmark:", error);
      setBookmarked(bookmarked);
    }
  };

  const toggleMute = (e) => {
    e.stopPropagation();
    setIsMuted((prev) => !prev);
  };

  const toggleAudioPlay = (e) => {
    e.stopPropagation();
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const renderMediaPreview = () => {
    const isVideo = contentType === 'video' || (mediaUrl && mediaUrl.match(/\.(mp4|webm|ogg)$/i));
    const isAudio = contentType === 'audio' || (mediaUrl && mediaUrl.match(/\.(mp3|wav|ogg)$/i));

    if (isVideo) {
      return (
        <div className="relative w-full h-full group/video">
          <video 
            ref={videoRef}
            src={mediaUrl} 
            poster={thumbnailUrl} 
            muted={isMuted}
            loop
            playsInline
            className="w-full h-full object-cover transition-transform duration-500 group-hover/video:scale-105"
          />
          {/* Video Control Overlay */}
          <div className="absolute bottom-2 right-2 flex items-center gap-1.5 z-10 opacity-0 group-hover/video:opacity-100 transition-opacity">
            <button
              type="button"
              onClick={toggleMute}
              className="p-1.5 rounded-lg bg-slate-950/80 hover:bg-slate-900 text-slate-200 backdrop-blur-md border border-slate-700/50 transition"
              title={isMuted ? "Unmute" : "Mute"}
            >
              {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5 text-emerald-400" />}
            </button>
          </div>
        </div>
      );
    }

    if (isAudio) {
      return (
        <div className="w-full h-full bg-slate-900 flex flex-col items-center justify-center p-4 relative group/audio">
          <Music className={`w-10 h-10 mb-2 transition ${isPlaying ? 'text-emerald-400 animate-bounce' : 'text-slate-500'}`} />
          <button
            type="button"
            onClick={toggleAudioPlay}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 text-xs font-semibold hover:bg-emerald-500/30 transition"
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-emerald-400" />}
            <span>{isPlaying ? 'Pause' : 'Preview Audio'}</span>
          </button>
          <audio 
            ref={audioRef}
            src={mediaUrl} 
            onEnded={() => setIsPlaying(false)}
            className="hidden" 
          />
        </div>
      );
    }

    if (thumbnailUrl || mediaUrl) {
      return (
        <img
          src={thumbnailUrl || mediaUrl}
          alt={currentPost?.title || "User media"}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 ease-out"
        />
      );
    }

    return (
      <div className="w-full h-full bg-slate-900 flex flex-col items-center justify-center text-slate-600">
        <ImageIcon className="w-10 h-10 mb-1" />
        <span className="text-[10px] text-slate-500">No media preview</span>
      </div>
    );
  };

  return (
    <>
      <div 
        onClick={handleCardClick}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden flex flex-col justify-between hover:border-emerald-500/50 hover:shadow-emerald-950/40 hover:-translate-y-1 transition-all duration-300 shadow-xl cursor-pointer group relative"
      >
        <div>
          <div className="relative aspect-video bg-slate-950 overflow-hidden">
            {renderMediaPreview()}
            
            <div className="absolute top-3 left-3 flex gap-2 z-10">
              <span className="text-[10px] uppercase bg-slate-950/80 backdrop-blur-md text-emerald-300 px-2.5 py-1 rounded-md font-bold tracking-wider border border-emerald-500/30 shadow-md">
                {contentType}
              </span>
            </div>

            {currentPost?.duration && (
              <span className="absolute bottom-3 right-3 bg-black/80 text-slate-200 text-[10px] font-semibold px-2 py-0.5 rounded backdrop-blur-sm z-10">
                {currentPost.duration} min
              </span>
            )}
          </div>

          <div className="p-5">
            {Array.isArray(currentPost?.categories) && currentPost.categories.length > 0 && (
              <div className="flex gap-1.5 mb-2.5 flex-wrap">
                {currentPost.categories.map((cat, idx) => (
                  <span key={cat?.id || idx} className="text-[10px] bg-emerald-950/60 text-emerald-300 px-2 py-0.5 rounded border border-emerald-500/30 font-medium">
                    {typeof cat === 'string' ? cat : (cat?.name || '')}
                  </span>
                ))}
              </div>
            )}

            {currentPost?.title && (
              <h3 className="text-slate-100 font-extrabold text-base mb-2 line-clamp-2 group-hover:text-emerald-400 transition-colors duration-200">
                {currentPost.title}
              </h3>
            )}

            {(currentPost?.summary || currentPost?.description) && (
              <p className="text-slate-300 text-xs mb-4 line-clamp-2 leading-relaxed">
                {currentPost.summary || currentPost.description}
              </p>
            )}

            <div className="flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-3">
              {authorName && (
                <Link
                  to={authorId ? `/profile/${authorId}` : '#'}
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-2 group/author hover:opacity-90 transition"
                >
                  {currentPost?.author?.profile_image ? (
                    <img 
                      src={currentPost.author.profile_image} 
                      alt={authorName} 
                      className="w-6 h-6 rounded-full object-cover border border-slate-700 group-hover/author:border-emerald-400 transition"
                    />
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-emerald-500/20 flex items-center justify-center text-[10px] font-bold text-emerald-400 border border-emerald-500/40 group-hover/author:border-emerald-400 transition">
                      {authorName[0]?.toUpperCase()}
                    </div>
                  )}
                  <span className="text-slate-200 font-semibold group-hover/author:text-emerald-400 group-hover/author:underline transition text-xs">
                    {authorName}
                  </span>
                </Link>
              )}
              {currentPost?.created_at && (
                <span className="text-slate-400">{new Date(currentPost.created_at).toLocaleDateString()}</span>
              )}
            </div>
          </div>
        </div>

        <div className="px-5 py-3 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between text-xs text-slate-300">
          <span className="text-emerald-400 text-[11px] font-mono font-medium">
            {Array.isArray(currentPost?.hashtags) 
              ? currentPost.hashtags.map(t => t.startsWith('#') ? t : `#${t}`).join(' ') 
              : (currentPost?.hashtags || '')}
          </span>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 text-slate-300" title="Views">
              <Eye className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-medium">{currentPost?.views_count || 0}</span>
            </div>

            <div className="flex items-center gap-1.5 text-slate-300" title="Comments">
              <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-medium">{currentPost?.comments_count || 0}</span>
            </div>

            <button 
              type="button"
              onClick={handleLike} 
              className={`flex items-center gap-1.5 transition cursor-pointer ${liked ? 'text-rose-500 font-bold' : 'text-slate-300 hover:text-rose-400'}`}
            >
              <Heart className={`w-4 h-4 ${liked ? 'fill-rose-500 text-rose-500' : ''}`} />
              <span>{likesCount}</span>
            </button>

            <button 
              type="button"
              onClick={handleBookmark} 
              className={`transition cursor-pointer ${bookmarked ? 'text-emerald-400' : 'text-slate-300 hover:text-emerald-400'}`}
              title={bookmarked ? "Remove bookmark" : "Save post"}
            >
              <Bookmark className={`w-4 h-4 ${bookmarked ? 'fill-emerald-400 text-emerald-400' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {showAuthModal && (
        <div 
          onClick={(e) => { e.stopPropagation(); setShowAuthModal(false); }}
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div onClick={(e) => e.stopPropagation()} className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 shadow-2xl relative">
            <button onClick={() => setShowAuthModal(false)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-100 transition p-1">
              <X className="w-5 h-5" />
            </button>
            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-4">
              <LogIn className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-100 mb-2">Account Required</h3>
            <p className="text-slate-300 text-sm mb-6">Please log in to like or bookmark community content.</p>
            <div className="flex items-center gap-3">
              <button type="button" onClick={() => setShowAuthModal(false)} className="flex-1 px-4 py-2.5 rounded-xl border border-slate-700 text-slate-300 text-sm font-medium hover:bg-slate-800 transition">Cancel</button>
              <button type="button" onClick={() => window.location.href = '/login'} className="flex-1 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-400 to-teal-400 text-slate-950 font-bold text-sm shadow-md shadow-emerald-500/20">Log In</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}