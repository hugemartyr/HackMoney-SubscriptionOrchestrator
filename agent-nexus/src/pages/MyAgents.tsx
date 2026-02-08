import { useEffect, useState } from "react";
import { Bot, Play, Pause, Settings, Trash2, TrendingUp, Activity } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getAgents, updateAgentStatus, deleteAgent, addActivityLog, type Agent } from "@/lib/storage";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

function AgentCard({ agent, onUpdate }: { agent: Agent; onUpdate: () => void }) {
  const statusColors = {
    active: 'bg-primary/20 text-primary border-primary/30',
    paused: 'bg-warning/20 text-warning-foreground border-warning/30',
    stopped: 'bg-muted text-muted-foreground border-muted',
  };

  const typeIcons = {
    subscription: '💳',
    chess: '♟️',
    dca: '📈',
    custom: '🤖',
  };

  const handleToggleStatus = () => {
    const newStatus = agent.status === 'active' ? 'paused' : 'active';
    updateAgentStatus(agent.id, newStatus);
    addActivityLog({
      agentId: agent.id,
      agentName: agent.name,
      action: newStatus === 'active' ? 'Agent resumed' : 'Agent paused',
      status: 'success',
    });
    onUpdate();
  };

  const handleDelete = () => {
    deleteAgent(agent.id);
    addActivityLog({
      agentId: agent.id,
      agentName: agent.name,
      action: 'Agent deleted',
      status: 'success',
    });
    onUpdate();
  };

  return (
    <Card className="glass-card hover:border-primary/30 transition-all duration-300 group">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="text-2xl">{typeIcons[agent.type]}</div>
            <div>
              <CardTitle className="text-lg">{agent.name}</CardTitle>
              <CardDescription className="text-xs capitalize">{agent.type} Agent</CardDescription>
            </div>
          </div>
          <Badge variant="outline" className={statusColors[agent.status]}>
            {agent.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground line-clamp-2">{agent.description}</p>

        {/* Mini Stats */}
        <div className="grid grid-cols-3 gap-2">
          <div className="text-center p-2 rounded-lg bg-secondary/30">
            <p className="text-lg font-semibold">{agent.stats.transactions}</p>
            <p className="text-xs text-muted-foreground">Txns</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-secondary/30">
            <p className="text-lg font-semibold">{agent.stats.successRate}%</p>
            <p className="text-xs text-muted-foreground">Success</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-secondary/30">
            <p className="text-lg font-semibold">${agent.stats.totalValue.toLocaleString()}</p>
            <p className="text-xs text-muted-foreground">Value</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={handleToggleStatus}
          >
            {agent.status === 'active' ? (
              <>
                <Pause className="w-4 h-4 mr-1" /> Pause
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-1" /> Start
              </>
            )}
          </Button>
          <Button variant="outline" size="icon" className="shrink-0">
            <Settings className="w-4 h-4" />
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="icon" className="shrink-0 hover:bg-destructive/20 hover:text-destructive hover:border-destructive/30">
                <Trash2 className="w-4 h-4" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent className="glass-card">
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Agent</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete "{agent.name}"? This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleDelete} className="bg-destructive hover:bg-destructive/90">
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
}

export default function MyAgents() {
  const [agents, setAgents] = useState<Agent[]>([]);

  const loadAgents = () => {
    setAgents(getAgents());
  };

  useEffect(() => {
    loadAgents();
  }, []);

  const activeCount = agents.filter(a => a.status === 'active').length;
  const pausedCount = agents.filter(a => a.status === 'paused').length;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">My Agents</h1>
          <p className="text-muted-foreground mt-1">Manage and monitor your deployed agents</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="secondary" className="bg-primary/20 text-primary">
            <Activity className="w-3 h-3 mr-1" />
            {activeCount} Active
          </Badge>
          <Badge variant="secondary" className="bg-warning/20 text-warning-foreground">
            <Pause className="w-3 h-3 mr-1" />
            {pausedCount} Paused
          </Badge>
        </div>
      </div>

      {/* Agents Grid */}
      {agents.length === 0 ? (
        <Card className="glass-card">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <div className="w-16 h-16 rounded-2xl bg-secondary/50 flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No Agents Yet</h3>
            <p className="text-muted-foreground text-center max-w-sm">
              Head to the Agent Factory to create your first autonomous agent
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} onUpdate={loadAgents} />
          ))}
        </div>
      )}
    </div>
  );
}
