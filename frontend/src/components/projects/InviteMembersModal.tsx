import React, { useState } from 'react';
import { X, Plus, Mail, AlertCircle, Check, UserPlus } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import type { Project } from './ProjectCard';

interface InviteMembersModalProps {
  isOpen: boolean;
  onClose: () => void;
  project: Project | null;
  onInvite: (projectId: string, members: InviteMemberData[]) => Promise<void>;
  isLoading?: boolean;
}

export interface InviteMemberData {
  email: string;
  role: 'member' | 'admin';
  message?: string;
}

const MEMBER_ROLES = [
  { value: 'member', label: 'Member', description: 'Can view and contribute to the project' },
  { value: 'admin', label: 'Admin', description: 'Can manage project settings and members' },
] as const;

export const InviteMembersModal: React.FC<InviteMembersModalProps> = ({
  isOpen,
  onClose,
  project,
  onInvite,
  isLoading = false,
}) => {
  const [members, setMembers] = useState<InviteMemberData[]>([]);
  const [currentMember, setCurrentMember] = useState<InviteMemberData>({
    email: '',
    role: 'member',
    message: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [invitesSent, setInvitesSent] = useState<string[]>([]);

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const addMember = () => {
    const newErrors: Record<string, string> = {};

    if (!currentMember.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!validateEmail(currentMember.email)) {
      newErrors.email = 'Please enter a valid email address';
    } else if (members.some(m => m.email === currentMember.email)) {
      newErrors.email = 'This email is already in the invitation list';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setMembers(prev => [...prev, { ...currentMember }]);
    setCurrentMember({
      email: '',
      role: 'member',
      message: '',
    });
    setErrors({});
  };

  const removeMember = (email: string) => {
    setMembers(prev => prev.filter(m => m.email !== email));
  };

  const updateMemberRole = (email: string, role: 'member' | 'admin') => {
    setMembers(prev => prev.map(m => 
      m.email === email ? { ...m, role } : m
    ));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!project || members.length === 0) {
      setErrors({ submit: 'Please add at least one member to invite' });
      return;
    }

    try {
      await onInvite(project.id, members);
      setInvitesSent(members.map(m => m.email));
      
      // Clear form after successful invite
      setTimeout(() => {
        setMembers([]);
        setCurrentMember({
          email: '',
          role: 'member',
          message: '',
        });
        setInvitesSent([]);
        setErrors({});
        onClose();
      }, 2000);
    } catch (error) {
      console.error('Failed to send invitations:', error);
      setErrors({ submit: 'Failed to send invitations. Please try again.' });
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && currentMember.email.trim()) {
      e.preventDefault();
      addMember();
    }
  };

  if (!isOpen || !project) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle className="text-xl font-semibold">Invite Team Members</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Invite people to collaborate on "{project.name}"
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
        
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Add Member Section */}
            <div className="border rounded-lg p-4 bg-gray-50">
              <h3 className="text-sm font-medium text-foreground mb-3">Add New Member</h3>
              
              <div className="space-y-4">
                {/* Email Input */}
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-foreground mb-1">
                    Email Address
                  </label>
                  <Input
                    id="email"
                    type="email"
                    value={currentMember.email}
                    onChange={(e) => setCurrentMember(prev => ({ ...prev, email: e.target.value }))}
                    onKeyPress={handleKeyPress}
                    placeholder="Enter email address"
                    className={errors.email ? 'border-red-500' : ''}
                  />
                  {errors.email && (
                    <div className="flex items-center space-x-1 mt-1 text-red-600 text-sm">
                      <AlertCircle className="h-4 w-4" />
                      <span>{errors.email}</span>
                    </div>
                  )}
                </div>

                {/* Role Selection */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Role
                  </label>
                  <div className="space-y-2">
                    {MEMBER_ROLES.map((role) => (
                      <label key={role.value} className="flex items-start space-x-2">
                        <input
                          type="radio"
                          name="role"
                          value={role.value}
                          checked={currentMember.role === role.value}
                          onChange={(e) => setCurrentMember(prev => ({ 
                            ...prev, 
                            role: e.target.value as 'member' | 'admin' 
                          }))}
                          className="mt-1 text-blue-600"
                        />
                        <div>
                          <span className="text-sm font-medium">{role.label}</span>
                          <p className="text-xs text-muted-foreground">{role.description}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Personal Message */}
                <div>
                  <label htmlFor="message" className="block text-sm font-medium text-foreground mb-1">
                    Personal Message (Optional)
                  </label>
                  <textarea
                    id="message"
                    value={currentMember.message}
                    onChange={(e) => setCurrentMember(prev => ({ ...prev, message: e.target.value }))}
                    placeholder="Add a personal message to the invitation..."
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <Button
                  type="button"
                  onClick={addMember}
                  variant="outline"
                  size="sm"
                  disabled={!currentMember.email.trim()}
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add to Invitation List
                </Button>
              </div>
            </div>

            {/* Members List */}
            {members.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-foreground mb-3">
                  Members to Invite ({members.length})
                </h3>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {members.map((member) => (
                    <div
                      key={member.email}
                      className="flex items-center justify-between p-3 border rounded-lg bg-white"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
                          <Mail className="h-4 w-4 text-blue-600" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">{member.email}</p>
                          <p className="text-xs text-muted-foreground">
                            {MEMBER_ROLES.find(r => r.value === member.role)?.label}
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        {invitesSent.includes(member.email) && (
                          <div className="flex items-center space-x-1 text-green-600 text-sm">
                            <Check className="h-4 w-4" />
                            <span>Sent</span>
                          </div>
                        )}
                        
                        <select
                          value={member.role}
                          onChange={(e) => updateMemberRole(member.email, e.target.value as 'member' | 'admin')}
                          className="text-xs border rounded px-2 py-1"
                          disabled={invitesSent.includes(member.email)}
                        >
                          {MEMBER_ROLES.map((role) => (
                            <option key={role.value} value={role.value}>
                              {role.label}
                            </option>
                          ))}
                        </select>
                        
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => removeMember(member.email)}
                          className="h-8 w-8 p-0"
                          disabled={invitesSent.includes(member.email)}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Success Message */}
            {invitesSent.length > 0 && (
              <div className="flex items-center space-x-2 text-green-600 text-sm bg-green-50 p-3 rounded-lg">
                <Check className="h-4 w-4" />
                <span>Invitations sent successfully! Members will receive email notifications.</span>
              </div>
            )}

            {/* Submit Error */}
            {errors.submit && (
              <div className="flex items-center space-x-1 text-red-600 text-sm">
                <AlertCircle className="h-4 w-4" />
                <span>{errors.submit}</span>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isLoading || members.length === 0 || invitesSent.length > 0}
              >
                {isLoading ? (
                  'Sending...'
                ) : invitesSent.length > 0 ? (
                  'Invitations Sent'
                ) : (
                  <>
                    <UserPlus className="h-4 w-4 mr-2" />
                    Send Invitations ({members.length})
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};