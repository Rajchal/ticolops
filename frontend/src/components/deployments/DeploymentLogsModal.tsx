import React, { useState, useEffect, useRef } from 'react';
import { X, Download, RefreshCw, Search, Filter, Copy, Check } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import type { Deployment } from './DeploymentCard';

interface DeploymentLogsModalProps {
  isOpen: boolean;
  onClose: () => void;
  deployment: Deployment | null;
  isLoading?: boolean;
  onRefresh?: (deployment: Deployment) => void;
}

type LogLevel = 'all' | 'info' | 'warn' | 'error' | 'debug';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  source?: string;
}

const parseLogEntry = (logLine: string): LogEntry => {
  // Simple log parsing - in a real app, this would be more sophisticated
  const timestampMatch = logLine.match(/^\[([\d\-T:\.Z]+)\]/);
  const levelMatch = logLine.match(/\[(INFO|WARN|ERROR|DEBUG)\]/i);
  
  return {
    timestamp: timestampMatch ? timestampMatch[1] : new Date().toISOString(),
    level: levelMatch ? levelMatch[1].toLowerCase() as LogLevel : 'info',
    message: logLine,
    source: 'build',
  };
};

const getLogLevelColor = (level: LogLevel) => {
  switch (level) {
    case 'error':
      return 'text-red-600';
    case 'warn':
      return 'text-yellow-600';
    case 'info':
      return 'text-blue-600';
    case 'debug':
      return 'text-gray-600';
    default:
      return 'text-gray-800';
  }
};

export const DeploymentLogsModal: React.FC<DeploymentLogsModalProps> = ({
  isOpen,
  onClose,
  deployment,
  isLoading = false,
  onRefresh,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [levelFilter, setLevelFilter] = useState<LogLevel>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [copied, setCopied] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);

  const logEntries = deployment?.logs.map(parseLogEntry) || [];

  // Filter logs based on search and level
  const filteredLogs = logEntries.filter(entry => {
    const matchesSearch = !searchQuery || 
      entry.message.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesLevel = levelFilter === 'all' || entry.level === levelFilter;
    return matchesSearch && matchesLevel;
  });

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs, autoScroll]);

  // Handle manual scroll to disable auto-scroll
  const handleScroll = () => {
    if (logsContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current;
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
      setAutoScroll(isAtBottom);
    }
  };

  const handleCopyLogs = async () => {
    if (!deployment) return;
    
    try {
      const logsText = deployment.logs.join('\n');
      await navigator.clipboard.writeText(logsText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy logs:', error);
    }
  };

  const handleDownloadLogs = () => {
    if (!deployment) return;
    
    const logsText = deployment.logs.join('\n');
    const blob = new Blob([logsText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `deployment-${deployment.id}-logs.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!isOpen || !deployment) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-6xl h-[80vh] flex flex-col">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b">
          <div>
            <CardTitle className="text-xl font-semibold">Deployment Logs</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {deployment.repositoryName} • {deployment.commitHash.substring(0, 7)} • {deployment.branch}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        
        <CardContent className="flex-1 flex flex-col p-0">
          {/* Controls */}
          <div className="flex items-center justify-between p-4 border-b bg-gray-50">
            <div className="flex items-center space-x-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  type="text"
                  placeholder="Search logs..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 w-64"
                />
              </div>
              
              <div className="flex items-center space-x-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <select
                  value={levelFilter}
                  onChange={(e) => setLevelFilter(e.target.value as LogLevel)}
                  className="px-3 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                >
                  <option value="all">All Levels</option>
                  <option value="info">Info</option>
                  <option value="warn">Warning</option>
                  <option value="error">Error</option>
                  <option value="debug">Debug</option>
                </select>
              </div>
              
              <div className="text-sm text-muted-foreground">
                {filteredLogs.length} of {logEntries.length} entries
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <label className="flex items-center space-x-2 text-sm">
                <input
                  type="checkbox"
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                  className="text-blue-600"
                />
                <span>Auto-scroll</span>
              </label>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => onRefresh?.(deployment)}
                disabled={isLoading}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyLogs}
              >
                {copied ? (
                  <Check className="h-4 w-4 mr-2 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4 mr-2" />
                )}
                {copied ? 'Copied!' : 'Copy'}
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadLogs}
              >
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
            </div>
          </div>

          {/* Logs Display */}
          <div 
            ref={logsContainerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-auto bg-gray-900 text-gray-100 font-mono text-sm"
          >
            {filteredLogs.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-400">
                {searchQuery || levelFilter !== 'all' ? (
                  <div className="text-center">
                    <p>No logs match your filters</p>
                    <p className="text-xs mt-1">Try adjusting your search or filter settings</p>
                  </div>
                ) : (
                  <div className="text-center">
                    <p>No logs available</p>
                    <p className="text-xs mt-1">Logs will appear here as the deployment progresses</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-4 space-y-1">
                {filteredLogs.map((entry, index) => (
                  <div key={index} className="flex items-start space-x-3 hover:bg-gray-800 px-2 py-1 rounded">
                    <span className="text-gray-500 text-xs whitespace-nowrap">
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={`text-xs font-medium uppercase whitespace-nowrap ${getLogLevelColor(entry.level)}`}>
                      {entry.level}
                    </span>
                    <span className="flex-1 whitespace-pre-wrap break-words">
                      {entry.message}
                    </span>
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>

          {/* Status Bar */}
          <div className="flex items-center justify-between p-3 border-t bg-gray-50 text-sm text-muted-foreground">
            <div className="flex items-center space-x-4">
              <span>Status: {deployment.status}</span>
              {deployment.buildDuration && (
                <span>Duration: {Math.floor(deployment.buildDuration / 60)}m {deployment.buildDuration % 60}s</span>
              )}
              {deployment.completedAt && (
                <span>Completed: {new Date(deployment.completedAt).toLocaleString()}</span>
              )}
            </div>
            
            <div className="flex items-center space-x-2">
              {deployment.status === 'building' && (
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
                  <span>Building...</span>
                </div>
              )}
              
              {!autoScroll && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setAutoScroll(true);
                    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className="text-xs"
                >
                  Scroll to Bottom
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};