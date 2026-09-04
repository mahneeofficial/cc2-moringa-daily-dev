import { useState, useEffect } from 'react';
import axios from 'axios';
import Navbar from '../components/Navbar';
import SidebarLeft from '../components/SidebarLeft';
import SidebarRight from '../components/SidebarRight';
import ContentCard from '../components/ContentCard';

export default function HomePage() {
  const [posts, setPosts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [currentTab, setCurrentTab] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleTabChange = (tab) => {
    setLoading(true);
    setCurrentTab(tab);
    setMobileMenuOpen(false); // Close mobile drawer on selection
  };

  // Function to update a single post in state immediately when liked/bookmarked
  const handlePostUpdate = (updatedPost) => {
    setPosts(prevPosts =>
      prevPosts.map(p => {
        const pId = p.content_id || p.ContentID || p.id;
        const uId = updatedPost.content_id || updatedPost.ContentID || updatedPost.id;
        return pId === uId ? updatedPost : p;
      })
    );
  };

  // Fetch categories from backend database
 useEffect(() => {
  axios.get('http://localhost:5001/api/categories')
    .then((res) => {
      const catArray = Array.isArray(res.data) ? res.data : (res.data?.categories || res.data?.items || []);
      setCategories(catArray);
    })
    .catch((err) => console.error("Error fetching categories:", err));
}, []);

  // Fetch content feed from backend database (Checks all possible token keys)
  // Fetch content feed from backend database
useEffect(() => {
  const url = currentTab.toLowerCase() === 'all'
    ? 'http://localhost:5001/api/content'
    : `http://localhost:5001/api/content?category=${currentTab}`;

  const token = 
    localStorage.getItem('token') || 
    localStorage.getItem('access_token') || 
    localStorage.getItem('jwt') || 
    localStorage.getItem('accessToken');

  axios.get(url, {
    headers: {
      ...(token && { Authorization: `Bearer ${token}` })
    }
  })
    .then((res) => {
      const itemsArray = res.data?.items || (Array.isArray(res.data) ? res.data : []);
      setPosts(itemsArray);
      setLoading(false);
    })
    .catch((err) => {
      console.error("Error fetching content feed:", err);
      setLoading(false);
    });
}, [currentTab]);
  // Filter posts based on search input
  const filteredPosts = posts.filter((post) => {
    const title = post.Title || post.title || '';
    const description = post.Description || post.description || '';
    return (
      title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      description.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  return (
    <div className="min-h-screen bg-[#0b0e14] text-slate-100 flex flex-col font-sans">
      {/* Top Navbar with Mobile Menu Toggle */}
      <Navbar 
        searchQuery={searchQuery} 
        setSearchQuery={setSearchQuery} 
        onToggleMobileMenu={() => setMobileMenuOpen(!mobileMenuOpen)} 
      />

      {/* Main Container */}
      <div className="flex flex-1 relative overflow-hidden">
        
        {/* Left Sidebar (Desktop: Fixed width, Mobile: Slide-out Drawer) */}
        <div className={`
          fixed lg:static inset-y-0 left-0 z-50 transform 
          ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'} 
          transition-transform duration-300 ease-in-out bg-[#0b0e14] border-r border-slate-800
        `}>
          <SidebarLeft 
            categories={categories} 
            currentTab={currentTab} 
            setCurrentTab={handleTabChange} 
          />
        </div>

        {/* Mobile Backdrop Overlay */}
        {mobileMenuOpen && (
          <div 
            onClick={() => setMobileMenuOpen(false)} 
            className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          />
        )}

        {/* Main Feed Content Area */}
        <main className="flex-1 p-4 md:p-6 overflow-y-auto w-full">
          
          {/* Horizontal Category Sub-Bar (Figma Style for Laptop/Tablet) */}
          <div className="hidden md:flex items-center gap-2 overflow-x-auto pb-3 mb-6 border-b border-slate-800/80 scrollbar-none">
            <button
              onClick={() => setCurrentTab('All')}
              className={`px-4 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition ${
                currentTab.toLowerCase() === 'all'
                  ? 'bg-emerald-500 text-slate-950 font-semibold shadow-md shadow-emerald-500/20'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              All
            </button>
            {categories.map((cat) => {
              const isSelected = currentTab.toLowerCase() === cat.name.toLowerCase();
              return (
                <button
                  key={cat.id}
                  onClick={() => setCurrentTab(cat.name)}
                  className={`px-4 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition ${
                    isSelected
                      ? 'bg-emerald-500 text-slate-950 font-semibold shadow-md shadow-emerald-500/20'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  {cat.name}
                </button>
              );
            })}
          </div>

          {/* Feed Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-sm font-semibold text-slate-400">{filteredPosts.length} posts</h2>
            <div className="flex gap-1 bg-[#121620] p-1 rounded-lg border border-slate-800 text-xs">
              <button className="px-3 py-1 bg-slate-800 text-slate-200 rounded font-medium">Trending</button>
              <button className="px-3 py-1 text-slate-400 hover:text-slate-200">Latest</button>
              <button className="px-3 py-1 text-slate-400 hover:text-slate-200">Liked</button>
            </div>
          </div>

          {/* Posts Grid (1 col on mobile, 2 cols on laptop) */}
          {loading ? (
            <div className="text-center py-20 text-slate-500">Loading database records...</div>
          ) : filteredPosts.length === 0 ? (
            <div className="text-center py-20 text-slate-500">No records found matching your search.</div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              {filteredPosts.map((post) => (
                <ContentCard 
                  key={post.content_id || post.ContentID || post.id} 
                  post={post} 
                  onUpdate={handlePostUpdate} 
                />
              ))}
            </div>
          )}
        </main>

        {/* Right Sidebar (Hidden on mobile/tablet, visible on large screens) */}
        <div className="hidden xl:block w-80 border-l border-slate-800 bg-[#0b0e14]">
          <SidebarRight posts={posts} />
        </div>

      </div>
    </div>
  );
}