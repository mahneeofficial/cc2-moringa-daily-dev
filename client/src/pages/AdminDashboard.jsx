import { useEffect, useState } from "react";
import { Users, FileWarning, Flag, Check, X, Ban, CheckCircle2, Loader2 } from "lucide-react";
import { listUsers, toggleUserActive, listPendingContent, listReports, resolveReport } from "../services/adminApi";
import { approveContent, flagContent } from "../services/contentApi";
import { roleLabel, roleColorClass, timeAgo } from "../utils/format";
import EmptyState from "../components/ui/EmptyState";

const TABS = [
  { id: "queue", label: "Content queue", icon: FileWarning },
  { id: "users", label: "Users", icon: Users },
  { id: "reports", label: "Reports", icon: Flag },
];

export default function AdminDashboard() {
  const [tab, setTab] = useState("queue");

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-mono text-sky-600 mb-1">// admin</p>
        <h1 className="text-2xl font-bold text-navy">Admin dashboard</h1>
      </div>

      <div className="flex gap-1 border-b border-line">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 -mb-px transition font-medium ${
              tab === id ? "border-sky-600 text-sky-600" : "border-transparent text-muted hover:text-navy"
            }`}
          >
            <Icon className="w-3.5 h-3.5" /> {label}
          </button>
        ))}
      </div>

      {tab === "queue" && <ContentQueueTab />}
      {tab === "users" && <UsersTab />}
      {tab === "reports" && <ReportsTab />}
    </div>
  );
}

function ContentQueueTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const data = await listPendingContent();
      setItems(data || []);
    } catch (err) {
      console.error("Failed to fetch pending content:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleApprove(id) {
    setProcessingId(id);
    try {
      await approveContent(id);
      await load();
    } catch (err) {
      console.error("Failed to approve content:", err);
    } finally {
      setProcessingId(null);
    }
  }

  async function handleFlag(id) {
    setProcessingId(id);
    try {
      await flagContent(id);
      await load();
    } catch (err) {
      console.error("Failed to flag content:", err);
    } finally {
      setProcessingId(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading queue...
      </div>
    );
  }

  if (items.length === 0) {
    return <EmptyState icon={CheckCircle2} title="Queue is clear" description="No content is waiting on review right now." />;
  }

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const categoryName = item.categories?.[0]?.name || item.category?.name || "Uncategorized";
        const authorName = item.author?.username || item.author || "Unknown";
        const isProcessing = processingId === item.id;

        return (
          <div key={item.id} className="p-4 rounded-xl border border-line bg-white shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[11px] font-mono uppercase text-muted">{categoryName}</span>
                  <span
                    className={`text-[10px] font-mono uppercase rounded px-1.5 py-0.5 border ${
                      item.status?.toLowerCase() === "archived" || item.status?.toLowerCase() === "flagged"
                        ? "text-red-600 border-red-300 bg-red-50"
                        : "text-amber-600 border-amber-400 bg-amber-50"
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
                <h3 className="font-display font-semibold text-navy">{item.title}</h3>
                <p className="text-xs text-muted mt-1">
                  by {authorName} · {timeAgo(item.createdAt)}
                </p>
              </div>

              <div className="flex gap-2 shrink-0">
                <button
                  disabled={isProcessing}
                  onClick={() => handleApprove(item.id)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-50 border border-emerald-500/30 text-emerald-600 hover:bg-emerald-100 disabled:opacity-50 transition"
                >
                  {isProcessing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />} Approve
                </button>
                <button
                  disabled={isProcessing}
                  onClick={() => handleFlag(item.id)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 border border-red-500/30 text-red-600 hover:bg-red-100 disabled:opacity-50 transition"
                >
                  {isProcessing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <X className="w-3.5 h-3.5" />} Flag
                </button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function UsersTab() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const data = await listUsers();
      setUsers(data || []);
    } catch (err) {
      console.error("Failed to list users:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleToggle(id) {
    setProcessingId(id);
    try {
      await toggleUserActive(id);
      await load();
    } catch (err) {
      console.error("Failed to toggle user status:", err);
    } finally {
      setProcessingId(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading users...
      </div>
    );
  }

  return (
    <div className="border border-line rounded-xl overflow-hidden bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-surface/95 text-muted text-[11px] uppercase font-mono border-b border-line">
          <tr>
            <th className="text-left px-4 py-2.5 font-medium">Username</th>
            <th className="text-left px-4 py-2.5 font-medium">Role</th>
            <th className="text-left px-4 py-2.5 font-medium">Status</th>
            <th className="text-right px-4 py-2.5 font-medium">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {users.map((u) => {
            const isProcessing = processingId === u.id;

            return (
              <tr key={u.id} className="hover:bg-slate-50/50 transition">
                <td className="px-4 py-3 text-navy font-medium">{u.username}</td>
                <td className={`px-4 py-3 font-mono text-xs ${roleColorClass(u.role)}`}>{roleLabel(u.role)}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs font-mono ${u.isActive ? "text-emerald-600" : "text-slate-400"}`}>
                    {u.isActive ? "Active" : "Deactivated"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    disabled={isProcessing}
                    onClick={() => handleToggle(u.id)}
                    className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium border transition disabled:opacity-50 ${
                      u.isActive
                        ? "border-red-500/30 text-red-600 bg-red-50 hover:bg-red-100"
                        : "border-emerald-500/30 text-emerald-600 bg-emerald-50 hover:bg-emerald-100"
                    }`}
                  >
                    {isProcessing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Ban className="w-3 h-3" />}
                    {u.isActive ? "Deactivate" : "Reactivate"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ReportsTab() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const data = await listReports();
      setReports(data || []);
    } catch (err) {
      console.error("Failed to list reports:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleResolve(id) {
    setProcessingId(id);
    try {
      await resolveReport(id);
      await load();
    } catch (err) {
      console.error("Failed to resolve report:", err);
    } finally {
      setProcessingId(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading reports...
      </div>
    );
  }

  if (reports.length === 0) {
    return <EmptyState icon={Flag} title="No reports" description="Content flagged by the community will show up here." />;
  }

  return (
    <div className="space-y-3">
      {reports.map((r) => {
        const title = r.contentTitle || r.content?.title || "Untitled Content";
        const reporterName = r.reporterUsername || r.reporter?.username || `User #${r.reportedBy || "Unknown"}`;
        const isResolved = r.status && r.status.toLowerCase() === "resolved";
        const isProcessing = processingId === r.id;

        return (
          <div key={r.id} className="p-4 rounded-xl border border-line bg-white shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-navy">{title}</p>
                <p className="text-xs text-muted mt-0.5">
                  Reported by <span className="font-medium text-slate-700">{reporterName}</span> · {timeAgo(r.createdAt)}
                </p>
                <p className="text-xs text-slate-600 mt-2 italic bg-slate-50 p-2 rounded border border-slate-100">
                  "{r.reason}"
                </p>
              </div>
              {!isResolved ? (
                <button
                  disabled={isProcessing}
                  onClick={() => handleResolve(r.id)}
                  className="shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-50 border border-emerald-500/30 text-emerald-600 hover:bg-emerald-100 disabled:opacity-50 transition"
                >
                  {isProcessing && <Loader2 className="w-3 h-3 animate-spin" />}
                  Mark resolved
                </button>
              ) : (
                <span className="text-[11px] font-mono text-emerald-600 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded shrink-0">
                  Resolved
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}