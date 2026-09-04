import { useEffect, useState } from "react";
import { Users, FileWarning, Flag, Check, X, Ban, CheckCircle2 } from "lucide-react";
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
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 -mb-px transition ${
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

  function load() {
    setLoading(true);
    listPendingContent().then((data) => {
      setItems(data);
      setLoading(false);
    });
  }
  useEffect(load, []);

  async function handleApprove(id) {
    await approveContent(id);
    load();
  }
  async function handleFlag(id) {
    await flagContent(id);
    load();
  }

  if (loading) return null;
  if (items.length === 0) {
    return <EmptyState icon={CheckCircle2} title="Queue is clear" description="No content is waiting on review right now." />;
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.id} className="p-4 rounded-xl border border-line bg-white">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[11px] font-mono uppercase text-muted">{item.category?.name}</span>
                <span
                  className={`text-[10px] font-mono uppercase rounded px-1.5 py-0.5 border ${
                    item.status === "Archived" || item.status === "flagged" ? "text-red-600 border-red-300" : "text-amber-600 border-amber-400"
                  }`}
                >
                  {item.status}
                </span>
              </div>
              <h3 className="font-display font-semibold text-navy">{item.title}</h3>
              <p className="text-xs text-muted mt-1">
                by {item.author?.username || item.author} · {timeAgo(item.createdAt)}
              </p>
            </div>
            <div className="flex gap-2 shrink-0">
              <button
                onClick={() => handleApprove(item.id)}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20"
              >
                <Check className="w-3.5 h-3.5" /> Approve
              </button>
              <button
                onClick={() => handleFlag(item.id)}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20"
              >
                <X className="w-3.5 h-3.5" /> Flag
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function UsersTab() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    listUsers().then((data) => {
      setUsers(data);
      setLoading(false);
    });
  }
  useEffect(load, []);

  async function handleToggle(id) {
    await toggleUserActive(id);
    load();
  }

  if (loading) return null;

  return (
    <div className="border border-line rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-surface/95 text-muted text-[11px] uppercase font-mono">
          <tr>
            <th className="text-left px-4 py-2.5 font-medium">Username</th>
            <th className="text-left px-4 py-2.5 font-medium">Role</th>
            <th className="text-left px-4 py-2.5 font-medium">Status</th>
            <th className="text-right px-4 py-2.5 font-medium">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {users.map((u) => (
            <tr key={u.id}>
              <td className="px-4 py-3 text-navy">{u.username}</td>
              <td className={`px-4 py-3 font-mono text-xs ${roleColorClass(u.role)}`}>{roleLabel(u.role)}</td>
              <td className="px-4 py-3">
                <span className={`text-xs font-mono ${u.isActive ? "text-emerald-400" : "text-muted"}`}>
                  {u.isActive ? "Active" : "Deactivated"}
                </span>
              </td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={() => handleToggle(u.id)}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium border transition ${
                    u.isActive
                      ? "border-red-500/30 text-red-400 hover:bg-red-500/10"
                      : "border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
                  }`}
                >
                  <Ban className="w-3 h-3" /> {u.isActive ? "Deactivate" : "Reactivate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReportsTab() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    listReports().then((data) => {
      setReports(data);
      setLoading(false);
    });
  }
  useEffect(load, []);

  async function handleResolve(id) {
    await resolveReport(id);
    load();
  }

  if (loading) return null;
  if (reports.length === 0) {
    return <EmptyState icon={Flag} title="No reports" description="Content flagged by the community will show up here." />;
  }

  return (
    <div className="space-y-3">
      {reports.map((r) => (
        <div key={r.id} className="p-4 rounded-xl border border-line bg-white">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm text-navy">{r.content?.title}</p>
              <p className="text-xs text-muted mt-1">Reported by {r.reporter?.username} · {timeAgo(r.createdAt)}</p>
              <p className="text-xs text-muted mt-2 italic">"{r.reason}"</p>
            </div>
            {r.status && r.status.toLowerCase() !== "resolved" ? (
              <button
                onClick={() => handleResolve(r.id)}
                className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20"
              >
                Mark resolved
              </button>
            ) : (
              <span className="text-[11px] font-mono text-muted shrink-0">Resolved</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

