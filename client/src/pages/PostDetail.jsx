import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Share2, Flag, ThumbsUp, ThumbsDown, Bookmark, Play, Volume2, MessageSquare } from 'lucide-react';
import apiRequest from '../services/api';

export default function PostDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [commentText, setCommentText] = useState('');

  useEffect(() => {
    apiRequest(`/api/posts/${id}`)
      .then((data) => {
        setPost(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch post details:', err);
        setError('Could not load content. It may have been removed or is pending review.');
        setLoading(false);
      });
  }, [id]);

  const handleCommentSubmit = async (e) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    
    try {
      const newComment = await apiRequest(`/api/posts/${id}/comments`, {
        method: 'POST',
        body: { body: commentText }
      });

      setPost((prev) => ({
        ...prev,
        comments: [newComment, ...(prev?.comments || [])]
      }));
      setCommentText('');
    } catch (err) {
      console.error('Error posting comment:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#07090e] text-slate-100 flex items-center justify-center">
        <p className="text-sm text-slate-400 animate-pulse">Loading content...</p>
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col items-center justify-center p-6">
        <p className="text-red-400 text-sm mb-4">{error || 'Post not found.'}</p>
        <Link to="/" className="text-xs bg-emerald-500 text-slate-950 font-bold px-4 py-2 rounded-xl">
          Back to Feed
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Back Button */}
        <button 
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-emerald-400 transition cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to feed</span>
        </button>

        {/* Thumbnail / Media Header Preview */}
        {(post.thumbnail_url || post.thumbnail || post.content_url) && (
          <div className="relative rounded-2xl overflow-hidden border border-slate-800 bg-slate-950 aspect-video max-h-[400px] w-full flex items-center justify-center">
            <img 
              src={post.thumbnail_url || post.thumbnail || post.content_url} 
              alt={post.title || post.Title} 
              className="w-full h-full object-cover" 
            />
            {post.content_type === 'video' && post.content_url && (
              <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                <div className="w-16 h-16 rounded-full bg-blue-500/90 text-white flex items-center justify-center shadow-xl">
                  <Play className="w-8 h-8 fill-white ml-1" />
                </div>
              </div>
            )}
            {post.content_type === 'podcast' && post.content_url && (
              <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                <div className="w-14 h-14 rounded-full bg-purple-500/90 text-white flex items-center justify-center shadow-xl">
                  <Volume2 className="w-7 h-7" />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Meta Badges */}
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="capitalize px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
            {post.content_type || 'Article'}
          </span>
          {post.category && <span className="text-slate-300 font-medium">{post.category.name}</span>}
          <span>•</span>
          <span>{post.duration ? `${post.duration} min read` : '5 min read'}</span>
        </div>

        {/* Title */}
        <h1 className="text-3xl font-bold font-serif text-white tracking-tight">{post.title || post.Title}</h1>

        {/* Author & Actions Bar */}
        <div className="flex items-center justify-between py-4 border-y border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-slate-800 overflow-hidden border border-slate-700 flex items-center justify-center font-bold text-slate-300">
              {post.author?.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-200">{post.author?.username || post.author_name || 'Community Creator'}</p>
              <p className="text-[11px] text-slate-500">{post.created_at ? new Date(post.created_at).toLocaleDateString() : ''}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:bg-slate-800 transition cursor-pointer">
              <Share2 className="w-3.5 h-3.5" /> Share
            </button>
            <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400 hover:text-red-400 transition cursor-pointer">
              <Flag className="w-3.5 h-3.5" /> Flag
            </button>
          </div>
        </div>

        {/* Summary / Excerpt */}
        {post.summary && (
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800/60 text-slate-300 text-xs italic">
            "{post.summary}"
          </div>
        )}

        {/* Full Description / Body */}
        <div className="prose prose-invert max-w-none text-slate-300 text-sm leading-relaxed whitespace-pre-wrap font-sans">
          {post.description || post.Description}
        </div>

        {/* Hashtags */}
        {post.hashtags && (
          <div className="flex flex-wrap gap-2 pt-4">
            {post.hashtags.split(',').map((tag, idx) => (
              <span key={idx} className="text-[11px] px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-400">
                {tag.trim().startsWith('#') ? tag.trim() : `#${tag.trim()}`}
              </span>
            ))}
          </div>
        )}

        {/* Like & Save Toolbar */}
        <div className="flex items-center justify-between pt-6 border-t border-slate-800">
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:border-emerald-500 transition cursor-pointer">
              <ThumbsUp className="w-4 h-4 text-emerald-400" /> {post.likes_count || 0}
            </button>
            <button className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:border-red-500 transition cursor-pointer">
              <ThumbsDown className="w-4 h-4 text-red-400" /> {post.dislikes_count || 0}
            </button>
          </div>
          <button className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:bg-slate-800 transition cursor-pointer">
            <Bookmark className="w-4 h-4" /> Save
          </button>
        </div>

        {/* Discussion / Comments Section */}
        <div className="pt-8 space-y-6 border-t border-slate-800">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-emerald-400" />
            <span>Discussion • {post.comments?.length || 0} comments</span>
          </h3>

          <form onSubmit={handleCommentSubmit} className="space-y-3">
            <textarea
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Share your thoughts..."
              className="w-full bg-[#0f131d] border border-slate-800 rounded-xl p-4 text-xs text-white placeholder-slate-600 h-24 focus:outline-none focus:border-emerald-500 resize-none transition"
              required
            />
            <div className="flex justify-end">
              <button
                type="submit"
                className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs px-6 py-2.5 rounded-xl transition cursor-pointer"
              >
                Post comment
              </button>
            </div>
          </form>

          {/* Comments List */}
          <div className="space-y-4">
            {post.comments && post.comments.length > 0 ? (
              post.comments.map((comment) => (
                <div key={comment.id} className="p-4 rounded-xl bg-[#0f131d] border border-slate-800/80 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-200">{comment.user?.username || 'Anonymous'}</span>
                    <span className="text-[10px] text-slate-500">{new Date(comment.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-xs text-slate-300">{comment.body}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 text-center py-6">No comments yet. Be the first to start the conversation.</p>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}