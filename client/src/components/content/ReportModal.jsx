import { useState } from 'react';
import { Flag, X, Send } from 'lucide-react';

const COMMON_REASONS = [
  "Spam or misleading content",
  "Harassment or hate speech",
  "Inappropriate or explicit media",
  "Misinformation or fake news",
  "Intellectual property or copyright violation",
  "Something else"
];

export default function ReportModal({ isOpen, onClose, onSubmit, isSubmitting }) {
  const [selectedReason, setSelectedReason] = useState(COMMON_REASONS[0]);
  const [additionalDetails, setAdditionalDetails] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const finalReason = selectedReason === "Something else" 
      ? `Other: ${additionalDetails}`
      : `${selectedReason}${additionalDetails ? ` - Details: ${additionalDetails}` : ''}`;
    
    onSubmit({
      reason_category: selectedReason,
      details: additionalDetails,
      full_reason: finalReason
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 w-full max-w-lg rounded-2xl p-6 shadow-2xl relative text-slate-100 animate-in fade-in zoom-in duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <Flag className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold">Report Post</h3>
              <p className="text-xs text-slate-400">Help keep MoringaHub safe and constructive</p>
            </div>
          </div>
          <button 
            type="button" 
            onClick={onClose} 
            className="p-1.5 text-slate-400 hover:text-slate-100 transition rounded-lg hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Options Form */}
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Select a reason:</p>
          
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {COMMON_REASONS.map((reason) => (
              <label 
                key={reason}
                className={`flex items-center gap-3 p-3 rounded-xl border transition cursor-pointer ${
                  selectedReason === reason 
                    ? 'bg-rose-500/10 border-rose-500/50 text-rose-300' 
                    : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                <input 
                  type="radio" 
                  name="report_reason" 
                  value={reason} 
                  checked={selectedReason === reason} 
                  onChange={() => setSelectedReason(reason)}
                  className="accent-rose-500"
                />
                <span className="text-xs font-medium">{reason}</span>
              </label>
            ))}
          </div>

          {/* Detailed Input Box */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              {selectedReason === "Something else" ? "Describe the issue *" : "Additional Details (Optional)"}
            </label>
            <textarea 
              rows={3}
              required={selectedReason === "Something else"}
              value={additionalDetails}
              onChange={(e) => setAdditionalDetails(e.target.value)}
              placeholder={selectedReason === "Something else" ? "Explain why this post breaks community rules..." : "Provide context for the moderation team..."}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-rose-500/50 resize-none"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button 
              type="button" 
              onClick={onClose} 
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 border border-slate-800 hover:bg-slate-800 transition"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              disabled={isSubmitting}
              className="flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold bg-rose-500 hover:bg-rose-600 text-white shadow-lg shadow-rose-950/40 transition disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              {isSubmitting ? "Submitting..." : "Send Report"}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}