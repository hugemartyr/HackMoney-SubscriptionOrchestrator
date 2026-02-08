import { useEffect, useState } from "react";
import { Activity, Bot, TrendingUp, Wallet, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getAgents, getActivityLogs, seedDemoData, type Agent, type ActivityLog } from "@/lib/storage";

function StatCard({ 
  title, 
  value, 
  change, 
  icon: Icon,
  trend 
}: { 
  title: string; 
  value: string; 
  change?: string;
  icon: React.ElementType;
  trend?: 'up' | 'down';
}) {
  return (
    <Card className="glass-card hover:border-primary/30 transition-all duration-300">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className="p-2 rounded-lg bg-primary/10">
          <Icon className="w-4 h-4 text-primary" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {change && (
          <div className={`flex items-center gap-1 text-xs mt-1 ${trend === 'up' ? 'text-primary' : 'text-destructive'}`}>
            {trend === 'up' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {change}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ActivityItem({ log }: { log: ActivityLog }) {
  const statusColors = {
    success: 'bg-primary/20 text-primary',
    pending: 'bg-warning/20 text-warning-foreground',
    failed: 'bg-destructive/20 text-destructive',
  };

  const timeAgo = (timestamp: string) => {
    const seconds = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors">
      <div className="flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse-glow" />
        <div>
          <p className="text-sm font-medium">{log.action}</p>
          <p className="text-xs text-muted-foreground">{log.agentName}</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Badge variant="secondary" className={statusColors[log.status]}>
          {log.status}
        </Badge>
        <span className="text-xs text-muted-foreground">{timeAgo(log.timestamp)}</span>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [logs, setLogs] = useState<ActivityLog[]>([]);

  useEffect(() => {
    seedDemoData();
    setAgents(getAgents());
    setLogs(getActivityLogs());
  }, []);

  const activeAgents = agents.filter(a => a.status === 'active').length;
  const totalValue = agents.reduce((sum, a) => sum + a.stats.totalValue, 0);
  const totalTransactions = agents.reduce((sum, a) => sum + a.stats.transactions, 0);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-1">Monitor your agent ecosystem</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Agents"
          value={activeAgents.toString()}
          change="+2 this week"
          icon={Bot}
          trend="up"
        />
        <StatCard
          title="Total Value Locked"
          value={`$${totalValue.toLocaleString()}`}
          change="+12.5%"
          icon={Wallet}
          trend="up"
        />
        <StatCard
          title="24h Settlements"
          value={totalTransactions.toString()}
          change="+8 today"
          icon={Activity}
          trend="up"
        />
        <StatCard
          title="Success Rate"
          value="99.2%"
          change="-0.1%"
          icon={TrendingUp}
          trend="down"
        />
      </div>

      {/* Activity Feed */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg">Recent Activity</CardTitle>
          <CardDescription>Latest agent actions and settlements</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {logs.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">No recent activity</p>
          ) : (
            logs.slice(0, 5).map((log) => (
              <ActivityItem key={log.id} log={log} />
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
