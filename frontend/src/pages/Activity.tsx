import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { ActivityFeed } from '../components/realtime/ActivityFeed';
import { TeamPresence } from '../components/realtime/TeamPresence';
import { ConflictAlerts } from '../components/realtime/ConflictAlerts';
import { DetailedConnectionStatus } from '../components/realtime/ConnectionStatus';
import { useRealtime } from '../contexts/RealtimeContext';
import { RefreshCw, Users, Activity as ActivityIcon, AlertTriangle } from 'lucide-react';

export const Activity: React.FC = () => {
  const { activities, userPresence, conflicts, clearActivities, isConnected } = useRealtime();
  const [activeTab, setActiveTab] = useState<'all' | 'team' | 'conflicts'>('all');

  const tabs = [
    { id: 'all', label: 'All Activity', icon: ActivityIcon, count: activities.length },
    { id: 'team', label: 'Team Presence', icon: Users, count: userPresence.length },
    { id: 'conflicts', label: 'Conflicts', icon: AlertTriangle, count: conflicts.length },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Team Activity</h1>
          <p className="text-muted-foreground">
            Real-time collaboration and activity monitoring
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            size="sm"
            onClick={clearActivities}
            disabled={!isConnected || activities.length === 0}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Clear History
          </Button>
        </div>
      </div>

      {/* Connection Status */}
      <DetailedConnectionStatus />

      {/* Tab Navigation */}
      <div className="border-b">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
                {tab.count > 0 && (
                  <span className="bg-muted text-muted-foreground rounded-full px-2 py-1 text-xs">
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {activeTab === 'all' && (
          <>
            <div className="lg:col-span-2">
              <ActivityFeed maxItems={50} showHeader={false} />
            </div>
            <div className="space-y-6">
              <TeamPresence maxUsers={20} />
              {conflicts.length > 0 && <ConflictAlerts maxAlerts={5} />}
            </div>
          </>
        )}

        {activeTab === 'team' && (
          <>
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle>Team Presence Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <TeamPresence maxUsers={50} showHeader={false} />
                </CardContent>
              </Card>
            </div>
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Presence Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Online</span>
                      <span className="text-sm font-medium text-green-600">
                        {userPresence.filter(u => u.status === 'online').length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Busy</span>
                      <span className="text-sm font-medium text-red-600">
                        {userPresence.filter(u => u.status === 'busy').length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Away</span>
                      <span className="text-sm font-medium text-yellow-600">
                        {userPresence.filter(u => u.status === 'away').length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Offline</span>
                      <span className="text-sm font-medium text-gray-600">
                        {userPresence.filter(u => u.status === 'offline').length}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <ActivityFeed maxItems={10} />
            </div>
          </>
        )}

        {activeTab === 'conflicts' && (
          <>
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle>Conflict Management</CardTitle>
                </CardHeader>
                <CardContent>
                  <ConflictAlerts maxAlerts={20} showHeader={false} />
                </CardContent>
              </Card>
            </div>
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Conflict Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">High Priority</span>
                      <span className="text-sm font-medium text-red-600">
                        {conflicts.filter(c => c.severity === 'high').length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Medium Priority</span>
                      <span className="text-sm font-medium text-yellow-600">
                        {conflicts.filter(c => c.severity === 'medium').length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Low Priority</span>
                      <span className="text-sm font-medium text-blue-600">
                        {conflicts.filter(c => c.severity === 'low').length}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <TeamPresence maxUsers={10} />
            </div>
          </>
        )}
      </div>
    </div>
  );
};