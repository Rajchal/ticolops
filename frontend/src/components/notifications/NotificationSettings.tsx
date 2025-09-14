import React, { useState } from 'react';
import { X, Bell, Mail, Smartphone, Volume2, VolumeX, Save, RefreshCw } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

interface NotificationPreferences {
  email: {
    enabled: boolean;
    activity: boolean;
    deployment: boolean;
    mentions: boolean;
    conflicts: boolean;
    system: boolean;
    digest: 'never' | 'daily' | 'weekly';
  };
  inApp: {
    enabled: boolean;
    activity: boolean;
    deployment: boolean;
    mentions: boolean;
    conflicts: boolean;
    system: boolean;
    sound: boolean;
  };
  push: {
    enabled: boolean;
    activity: boolean;
    deployment: boolean;
    mentions: boolean;
    conflicts: boolean;
    system: boolean;
  };
  quietHours: {
    enabled: boolean;
    startTime: string;
    endTime: string;
    timezone: string;
  };
  keywords: string[];
  projects: string[];
}

interface NotificationSettingsProps {
  isOpen: boolean;
  onClose: () => void;
  preferences: NotificationPreferences;
  onSave: (preferences: NotificationPreferences) => Promise<void>;
  availableProjects: Array<{ id: string; name: string }>;
  isLoading?: boolean;
}

const defaultPreferences: NotificationPreferences = {
  email: {
    enabled: true,
    activity: false,
    deployment: true,
    mentions: true,
    conflicts: true,
    system: false,
    digest: 'daily',
  },
  inApp: {
    enabled: true,
    activity: true,
    deployment: true,
    mentions: true,
    conflicts: true,
    system: true,
    sound: true,
  },
  push: {
    enabled: false,
    activity: false,
    deployment: true,
    mentions: true,
    conflicts: true,
    system: false,
  },
  quietHours: {
    enabled: false,
    startTime: '22:00',
    endTime: '08:00',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  },
  keywords: [],
  projects: [],
};

export const NotificationSettings: React.FC<NotificationSettingsProps> = ({
  isOpen,
  onClose,
  preferences,
  onSave,
  availableProjects,
  isLoading = false,
}) => {
  const [settings, setSettings] = useState<NotificationPreferences>(preferences);
  const [newKeyword, setNewKeyword] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave(settings);
      onClose();
    } catch (error) {
      console.error('Failed to save notification settings:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    setSettings(defaultPreferences);
  };

  const addKeyword = () => {
    if (newKeyword.trim() && !settings.keywords.includes(newKeyword.trim())) {
      setSettings(prev => ({
        ...prev,
        keywords: [...prev.keywords, newKeyword.trim()],
      }));
      setNewKeyword('');
    }
  };

  const removeKeyword = (keyword: string) => {
    setSettings(prev => ({
      ...prev,
      keywords: prev.keywords.filter(k => k !== keyword),
    }));
  };

  const toggleProject = (projectId: string) => {
    setSettings(prev => ({
      ...prev,
      projects: prev.projects.includes(projectId)
        ? prev.projects.filter(id => id !== projectId)
        : [...prev.projects, projectId],
    }));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b">
          <CardTitle className="text-xl font-semibold">Notification Settings</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        
        <CardContent className="p-6 space-y-8">
          {/* In-App Notifications */}
          <div>
            <h3 className="text-lg font-medium mb-4 flex items-center space-x-2">
              <Bell className="h-5 w-5" />
              <span>In-App Notifications</span>
            </h3>
            
            <div className="space-y-4">
              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={settings.inApp.enabled}
                  onChange={(e) => setSettings(prev => ({
                    ...prev,
                    inApp: { ...prev.inApp, enabled: e.target.checked }
                  }))}
                  className="text-blue-600"
                />
                <span className="font-medium">Enable in-app notifications</span>
              </label>
              
              {settings.inApp.enabled && (
                <div className="ml-6 space-y-3">
                  <label className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      checked={settings.inApp.sound}
                      onChange={(e) => setSettings(prev => ({
                        ...prev,
                        inApp: { ...prev.inApp, sound: e.target.checked }
                      }))}
                      className="text-blue-600"
                    />
                    <span className="flex items-center space-x-2">
                      {settings.inApp.sound ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                      <span>Play notification sounds</span>
                    </span>
                  </label>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.inApp.activity}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          inApp: { ...prev.inApp, activity: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>Team activity</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.inApp.deployment}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          inApp: { ...prev.inApp, deployment: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>Deployments</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.inApp.mentions}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          inApp: { ...prev.inApp, mentions: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>Mentions</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.inApp.conflicts}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          inApp: { ...prev.inApp, conflicts: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>Conflicts</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.inApp.system}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          inApp: { ...prev.inApp, system: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>System updates</span>
                    </label>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Email Notifications */}
          <div>
            <h3 className="text-lg font-medium mb-4 flex items-center space-x-2">
              <Mail className="h-5 w-5" />
              <span>Email Notifications</span>
            </h3>
            
            <div className="space-y-4">
              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={settings.email.enabled}
                  onChange={(e) => setSettings(prev => ({
                    ...prev,
                    email: { ...prev.email, enabled: e.target.checked }
                  }))}
                  className="text-blue-600"
                />
                <span className="font-medium">Enable email notifications</span>
              </label>
              
              {settings.email.enabled && (
                <div className="ml-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email digest frequency
                    </label>
                    <select
                      value={settings.email.digest}
                      onChange={(e) => setSettings(prev => ({
                        ...prev,
                        email: { ...prev.email, digest: e.target.value as 'never' | 'daily' | 'weekly' }
                      }))}
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="never">Never</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                    </select>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.email.activity}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          email: { ...prev.email, activity: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>Team activity</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.email.deployment}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          email: { ...prev.email, deployment: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>Deployments</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.email.mentions}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          email: { ...prev.email, mentions: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>Mentions</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.email.conflicts}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          email: { ...prev.email, conflicts: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>Conflicts</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.email.system}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          email: { ...prev.email, system: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>System updates</span>
                    </label>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Push Notifications */}
          <div>
            <h3 className="text-lg font-medium mb-4 flex items-center space-x-2">
              <Smartphone className="h-5 w-5" />
              <span>Push Notifications</span>
            </h3>
            
            <div className="space-y-4">
              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={settings.push.enabled}
                  onChange={(e) => setSettings(prev => ({
                    ...prev,
                    push: { ...prev.push, enabled: e.target.checked }
                  }))}
                  className="text-blue-600"
                />
                <span className="font-medium">Enable push notifications</span>
              </label>
              
              {settings.push.enabled && (
                <div className="ml-6">
                  <div className="grid grid-cols-2 gap-4">
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.push.activity}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          push: { ...prev.push, activity: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>Team activity</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.push.deployment}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          push: { ...prev.push, deployment: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>Deployments</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.push.mentions}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          push: { ...prev.push, mentions: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>Mentions</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.push.conflicts}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          push: { ...prev.push, conflicts: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>Conflicts</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={settings.push.system}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          push: { ...prev.push, system: e.target.checked }
                        }))}
                        className="text-blue-600"
                      />
                      <span>System updates</span>
                    </label>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Quiet Hours */}
          <div>
            <h3 className="text-lg font-medium mb-4">Quiet Hours</h3>
            
            <div className="space-y-4">
              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={settings.quietHours.enabled}
                  onChange={(e) => setSettings(prev => ({
                    ...prev,
                    quietHours: { ...prev.quietHours, enabled: e.target.checked }
                  }))}
                  className="text-blue-600"
                />
                <span className="font-medium">Enable quiet hours</span>
              </label>
              
              {settings.quietHours.enabled && (
                <div className="ml-6 grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Start time
                    </label>
                    <Input
                      type="time"
                      value={settings.quietHours.startTime}
                      onChange={(e) => setSettings(prev => ({
                        ...prev,
                        quietHours: { ...prev.quietHours, startTime: e.target.value }
                      }))}
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      End time
                    </label>
                    <Input
                      type="time"
                      value={settings.quietHours.endTime}
                      onChange={(e) => setSettings(prev => ({
                        ...prev,
                        quietHours: { ...prev.quietHours, endTime: e.target.value }
                      }))}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Keywords */}
          <div>
            <h3 className="text-lg font-medium mb-4">Keywords</h3>
            <p className="text-sm text-gray-600 mb-4">
              Get notified when these keywords are mentioned in activities or comments
            </p>
            
            <div className="space-y-4">
              <div className="flex space-x-2">
                <Input
                  type="text"
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
                  placeholder="Add keyword..."
                  className="flex-1"
                />
                <Button
                  type="button"
                  onClick={addKeyword}
                  variant="outline"
                  size="sm"
                  disabled={!newKeyword.trim()}
                >
                  Add
                </Button>
              </div>
              
              {settings.keywords.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {settings.keywords.map((keyword) => (
                    <div
                      key={keyword}
                      className="flex items-center space-x-1 bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-sm"
                    >
                      <span>{keyword}</span>
                      <button
                        type="button"
                        onClick={() => removeKeyword(keyword)}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Project Subscriptions */}
          <div>
            <h3 className="text-lg font-medium mb-4">Project Subscriptions</h3>
            <p className="text-sm text-gray-600 mb-4">
              Choose which projects you want to receive notifications for
            </p>
            
            <div className="grid grid-cols-2 gap-4">
              {availableProjects.map((project) => (
                <label key={project.id} className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={settings.projects.includes(project.id)}
                    onChange={() => toggleProject(project.id)}
                    className="text-blue-600"
                  />
                  <span>{project.name}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-between pt-6 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={handleReset}
              disabled={isSaving}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Reset to Defaults
            </Button>
            
            <div className="flex space-x-3">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isSaving}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={handleSave}
                disabled={isSaving}
              >
                {isSaving ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 mr-2" />
                )}
                {isSaving ? 'Saving...' : 'Save Settings'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};