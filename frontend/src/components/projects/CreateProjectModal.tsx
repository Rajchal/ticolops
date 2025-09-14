import React, { useState } from 'react';
import { X, Plus, AlertCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (projectData: CreateProjectData) => Promise<void>;
  isLoading?: boolean;
}

export interface CreateProjectData {
  name: string;
  description: string;
  visibility: 'public' | 'private';
  initialMembers?: string[];
}

export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
}) => {
  const [formData, setFormData] = useState<CreateProjectData>({
    name: '',
    description: '',
    visibility: 'private',
    initialMembers: [],
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [memberEmail, setMemberEmail] = useState('');

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Project name is required';
    } else if (formData.name.length < 3) {
      newErrors.name = 'Project name must be at least 3 characters';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Project description is required';
    } else if (formData.description.length < 10) {
      newErrors.description = 'Description must be at least 10 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    try {
      await onSubmit(formData);
      // Reset form on success
      setFormData({
        name: '',
        description: '',
        visibility: 'private',
        initialMembers: [],
      });
      setMemberEmail('');
      setErrors({});
      onClose();
    } catch (error) {
      console.error('Failed to create project:', error);
      setErrors({ submit: 'Failed to create project. Please try again.' });
    }
  };

  const addMember = () => {
    if (memberEmail.trim() && !formData.initialMembers?.includes(memberEmail.trim())) {
      setFormData(prev => ({
        ...prev,
        initialMembers: [...(prev.initialMembers || []), memberEmail.trim()],
      }));
      setMemberEmail('');
    }
  };

  const removeMember = (email: string) => {
    setFormData(prev => ({
      ...prev,
      initialMembers: prev.initialMembers?.filter(member => member !== email) || [],
    }));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && memberEmail.trim()) {
      e.preventDefault();
      addMember();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="text-xl font-semibold">Create New Project</CardTitle>
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
            {/* Project Name */}
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-foreground mb-2">
                Project Name *
              </label>
              <Input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Enter project name"
                className={errors.name ? 'border-red-500' : ''}
              />
              {errors.name && (
                <div className="flex items-center space-x-1 mt-1 text-red-600 text-sm">
                  <AlertCircle className="h-4 w-4" />
                  <span>{errors.name}</span>
                </div>
              )}
            </div>

            {/* Project Description */}
            <div>
              <label htmlFor="description" className="block text-sm font-medium text-foreground mb-2">
                Description *
              </label>
              <textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Describe your project..."
                rows={4}
                className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors.description ? 'border-red-500' : 'border-gray-300'
                }`}
              />
              {errors.description && (
                <div className="flex items-center space-x-1 mt-1 text-red-600 text-sm">
                  <AlertCircle className="h-4 w-4" />
                  <span>{errors.description}</span>
                </div>
              )}
            </div>

            {/* Visibility */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Visibility
              </label>
              <div className="space-y-2">
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    name="visibility"
                    value="private"
                    checked={formData.visibility === 'private'}
                    onChange={(e) => setFormData(prev => ({ ...prev, visibility: e.target.value as 'private' | 'public' }))}
                    className="text-blue-600"
                  />
                  <span className="text-sm">🔒 Private - Only invited members can access</span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    name="visibility"
                    value="public"
                    checked={formData.visibility === 'public'}
                    onChange={(e) => setFormData(prev => ({ ...prev, visibility: e.target.value as 'private' | 'public' }))}
                    className="text-blue-600"
                  />
                  <span className="text-sm">🌐 Public - Anyone can view and request to join</span>
                </label>
              </div>
            </div>

            {/* Initial Members */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Invite Team Members (Optional)
              </label>
              <div className="flex space-x-2 mb-3">
                <Input
                  type="email"
                  value={memberEmail}
                  onChange={(e) => setMemberEmail(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter email address"
                  className="flex-1"
                />
                <Button
                  type="button"
                  onClick={addMember}
                  variant="outline"
                  size="sm"
                  disabled={!memberEmail.trim()}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              
              {formData.initialMembers && formData.initialMembers.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Members to invite ({formData.initialMembers.length}):
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {formData.initialMembers.map((email) => (
                      <div
                        key={email}
                        className="flex items-center space-x-1 bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-sm"
                      >
                        <span>{email}</span>
                        <button
                          type="button"
                          onClick={() => removeMember(email)}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

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
                disabled={isLoading}
              >
                {isLoading ? 'Creating...' : 'Create Project'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};