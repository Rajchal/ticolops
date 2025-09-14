import React, { useState } from 'react';
import { X, GitBranch, AlertCircle, ExternalLink, CheckCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

interface ConnectRepositoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnect: (repositoryData: ConnectRepositoryData) => Promise<void>;
  projectId: string;
  projectName: string;
  isLoading?: boolean;
}

export interface ConnectRepositoryData {
  url: string;
  provider: 'github' | 'gitlab' | 'bitbucket';
  branch: string;
  accessToken?: string;
  autoDeployEnabled: boolean;
  buildCommand?: string;
  outputDirectory?: string;
  environmentVariables?: Record<string, string>;
}

const PROVIDERS = [
  {
    id: 'github' as const,
    name: 'GitHub',
    icon: '🐙',
    urlPattern: /^https:\/\/github\.com\/[\w\-\.]+\/[\w\-\.]+$/,
    example: 'https://github.com/username/repository',
  },
  {
    id: 'gitlab' as const,
    name: 'GitLab',
    icon: '🦊',
    urlPattern: /^https:\/\/gitlab\.com\/[\w\-\.]+\/[\w\-\.]+$/,
    example: 'https://gitlab.com/username/repository',
  },
  {
    id: 'bitbucket' as const,
    name: 'Bitbucket',
    icon: '🪣',
    urlPattern: /^https:\/\/bitbucket\.org\/[\w\-\.]+\/[\w\-\.]+$/,
    example: 'https://bitbucket.org/username/repository',
  },
];

export const ConnectRepositoryModal: React.FC<ConnectRepositoryModalProps> = ({
  isOpen,
  onClose,
  onConnect,
  projectId,
  projectName,
  isLoading = false,
}) => {
  const [step, setStep] = useState<'provider' | 'details' | 'configuration'>('provider');
  const [formData, setFormData] = useState<ConnectRepositoryData>({
    url: '',
    provider: 'github',
    branch: 'main',
    autoDeployEnabled: true,
    buildCommand: '',
    outputDirectory: '',
    environmentVariables: {},
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [envVarKey, setEnvVarKey] = useState('');
  const [envVarValue, setEnvVarValue] = useState('');

  const detectProvider = (url: string): 'github' | 'gitlab' | 'bitbucket' | null => {
    for (const provider of PROVIDERS) {
      if (provider.urlPattern.test(url)) {
        return provider.id;
      }
    }
    return null;
  };

  const validateUrl = (url: string): boolean => {
    const provider = detectProvider(url);
    return provider !== null;
  };

  const handleUrlChange = (url: string) => {
    setFormData(prev => ({ ...prev, url }));
    
    const provider = detectProvider(url);
    if (provider) {
      setFormData(prev => ({ ...prev, provider }));
      setErrors(prev => ({ ...prev, url: '' }));
    }
  };

  const handleNextStep = () => {
    const newErrors: Record<string, string> = {};

    if (step === 'provider') {
      if (!formData.url.trim()) {
        newErrors.url = 'Repository URL is required';
      } else if (!validateUrl(formData.url)) {
        newErrors.url = 'Please enter a valid repository URL';
      }

      if (Object.keys(newErrors).length === 0) {
        setStep('details');
      }
    } else if (step === 'details') {
      if (!formData.branch.trim()) {
        newErrors.branch = 'Branch name is required';
      }

      if (Object.keys(newErrors).length === 0) {
        setStep('configuration');
      }
    }

    setErrors(newErrors);
  };

  const handlePrevStep = () => {
    if (step === 'details') {
      setStep('provider');
    } else if (step === 'configuration') {
      setStep('details');
    }
  };

  const addEnvironmentVariable = () => {
    if (envVarKey.trim() && envVarValue.trim()) {
      setFormData(prev => ({
        ...prev,
        environmentVariables: {
          ...prev.environmentVariables,
          [envVarKey.trim()]: envVarValue.trim(),
        },
      }));
      setEnvVarKey('');
      setEnvVarValue('');
    }
  };

  const removeEnvironmentVariable = (key: string) => {
    setFormData(prev => {
      const newEnvVars = { ...prev.environmentVariables };
      delete newEnvVars[key];
      return { ...prev, environmentVariables: newEnvVars };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      await onConnect(formData);
      // Reset form on success
      setFormData({
        url: '',
        provider: 'github',
        branch: 'main',
        autoDeployEnabled: true,
        buildCommand: '',
        outputDirectory: '',
        environmentVariables: {},
      });
      setStep('provider');
      setErrors({});
      onClose();
    } catch (error) {
      console.error('Failed to connect repository:', error);
      setErrors({ submit: 'Failed to connect repository. Please check your credentials and try again.' });
    }
  };

  if (!isOpen) return null;

  const selectedProvider = PROVIDERS.find(p => p.id === formData.provider);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle className="text-xl font-semibold">Connect Repository</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Connect a Git repository to "{projectName}"
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
          {/* Step Indicator */}
          <div className="flex items-center justify-center mb-6">
            <div className="flex items-center space-x-4">
              <div className={`flex items-center space-x-2 ${
                step === 'provider' ? 'text-blue-600' : 'text-green-600'
              }`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  step === 'provider' ? 'bg-blue-100 text-blue-600' : 'bg-green-100 text-green-600'
                }`}>
                  {step === 'provider' ? '1' : <CheckCircle className="h-4 w-4" />}
                </div>
                <span className="text-sm">Repository</span>
              </div>
              
              <div className={`w-8 h-0.5 ${
                ['details', 'configuration'].includes(step) ? 'bg-green-500' : 'bg-gray-300'
              }`} />
              
              <div className={`flex items-center space-x-2 ${
                step === 'details' ? 'text-blue-600' : 
                step === 'configuration' ? 'text-green-600' : 'text-gray-400'
              }`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  step === 'details' ? 'bg-blue-100 text-blue-600' :
                  step === 'configuration' ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'
                }`}>
                  {step === 'configuration' ? <CheckCircle className="h-4 w-4" /> : '2'}
                </div>
                <span className="text-sm">Details</span>
              </div>
              
              <div className={`w-8 h-0.5 ${
                step === 'configuration' ? 'bg-blue-500' : 'bg-gray-300'
              }`} />
              
              <div className={`flex items-center space-x-2 ${
                step === 'configuration' ? 'text-blue-600' : 'text-gray-400'
              }`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  step === 'configuration' ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-400'
                }`}>
                  3
                </div>
                <span className="text-sm">Configuration</span>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Step 1: Provider Selection */}
            {step === 'provider' && (
              <div className="space-y-4">
                <div>
                  <label htmlFor="url" className="block text-sm font-medium text-foreground mb-2">
                    Repository URL
                  </label>
                  <Input
                    id="url"
                    type="url"
                    value={formData.url}
                    onChange={(e) => handleUrlChange(e.target.value)}
                    placeholder="https://github.com/username/repository"
                    className={errors.url ? 'border-red-500' : ''}
                  />
                  {errors.url && (
                    <div className="flex items-center space-x-1 mt-1 text-red-600 text-sm">
                      <AlertCircle className="h-4 w-4" />
                      <span>{errors.url}</span>
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Supported Providers
                  </label>
                  <div className="grid grid-cols-1 gap-3">
                    {PROVIDERS.map((provider) => (
                      <div
                        key={provider.id}
                        className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                          formData.provider === provider.id
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-300 hover:border-gray-400'
                        }`}
                        onClick={() => setFormData(prev => ({ ...prev, provider: provider.id }))}
                      >
                        <div className="flex items-center space-x-3">
                          <span className="text-2xl">{provider.icon}</span>
                          <div>
                            <h3 className="font-medium">{provider.name}</h3>
                            <p className="text-sm text-muted-foreground">{provider.example}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Repository Details */}
            {step === 'details' && (
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="text-2xl">{selectedProvider?.icon}</span>
                    <span className="font-medium">{selectedProvider?.name}</span>
                  </div>
                  <p className="text-sm text-muted-foreground break-all">{formData.url}</p>
                </div>

                <div>
                  <label htmlFor="branch" className="block text-sm font-medium text-foreground mb-2">
                    Branch
                  </label>
                  <div className="flex items-center space-x-2">
                    <GitBranch className="h-4 w-4 text-muted-foreground" />
                    <Input
                      id="branch"
                      type="text"
                      value={formData.branch}
                      onChange={(e) => setFormData(prev => ({ ...prev, branch: e.target.value }))}
                      placeholder="main"
                      className={errors.branch ? 'border-red-500' : ''}
                    />
                  </div>
                  {errors.branch && (
                    <div className="flex items-center space-x-1 mt-1 text-red-600 text-sm">
                      <AlertCircle className="h-4 w-4" />
                      <span>{errors.branch}</span>
                    </div>
                  )}
                </div>

                <div>
                  <label htmlFor="accessToken" className="block text-sm font-medium text-foreground mb-2">
                    Access Token (Optional)
                  </label>
                  <Input
                    id="accessToken"
                    type="password"
                    value={formData.accessToken || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, accessToken: e.target.value }))}
                    placeholder="For private repositories"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Required for private repositories. Create a personal access token in your Git provider settings.
                  </p>
                </div>
              </div>
            )}

            {/* Step 3: Configuration */}
            {step === 'configuration' && (
              <div className="space-y-6">
                <div>
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={formData.autoDeployEnabled}
                      onChange={(e) => setFormData(prev => ({ ...prev, autoDeployEnabled: e.target.checked }))}
                      className="text-blue-600"
                    />
                    <span className="text-sm font-medium">Enable automatic deployments</span>
                  </label>
                  <p className="text-xs text-muted-foreground mt-1 ml-6">
                    Automatically deploy when code is pushed to the selected branch
                  </p>
                </div>

                {formData.autoDeployEnabled && (
                  <>
                    <div>
                      <label htmlFor="buildCommand" className="block text-sm font-medium text-foreground mb-2">
                        Build Command (Optional)
                      </label>
                      <Input
                        id="buildCommand"
                        type="text"
                        value={formData.buildCommand || ''}
                        onChange={(e) => setFormData(prev => ({ ...prev, buildCommand: e.target.value }))}
                        placeholder="npm run build"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Command to build your application. Leave empty for auto-detection.
                      </p>
                    </div>

                    <div>
                      <label htmlFor="outputDirectory" className="block text-sm font-medium text-foreground mb-2">
                        Output Directory (Optional)
                      </label>
                      <Input
                        id="outputDirectory"
                        type="text"
                        value={formData.outputDirectory || ''}
                        onChange={(e) => setFormData(prev => ({ ...prev, outputDirectory: e.target.value }))}
                        placeholder="dist"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Directory containing the built application. Leave empty for auto-detection.
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-foreground mb-2">
                        Environment Variables
                      </label>
                      <div className="space-y-3">
                        <div className="flex space-x-2">
                          <Input
                            type="text"
                            value={envVarKey}
                            onChange={(e) => setEnvVarKey(e.target.value)}
                            placeholder="Variable name"
                            className="flex-1"
                          />
                          <Input
                            type="text"
                            value={envVarValue}
                            onChange={(e) => setEnvVarValue(e.target.value)}
                            placeholder="Variable value"
                            className="flex-1"
                          />
                          <Button
                            type="button"
                            onClick={addEnvironmentVariable}
                            variant="outline"
                            size="sm"
                            disabled={!envVarKey.trim() || !envVarValue.trim()}
                          >
                            Add
                          </Button>
                        </div>

                        {Object.entries(formData.environmentVariables || {}).length > 0 && (
                          <div className="space-y-2">
                            {Object.entries(formData.environmentVariables || {}).map(([key, value]) => (
                              <div key={key} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                                <span className="text-sm font-mono">{key}={value}</span>
                                <Button
                                  type="button"
                                  onClick={() => removeEnvironmentVariable(key)}
                                  variant="outline"
                                  size="sm"
                                  className="h-6 w-6 p-0"
                                >
                                  <X className="h-3 w-3" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}
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
            <div className="flex justify-between pt-4 border-t">
              <div>
                {step !== 'provider' && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handlePrevStep}
                    disabled={isLoading}
                  >
                    Previous
                  </Button>
                )}
              </div>
              
              <div className="flex space-x-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={onClose}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                
                {step === 'configuration' ? (
                  <Button
                    type="submit"
                    disabled={isLoading}
                  >
                    {isLoading ? 'Connecting...' : 'Connect Repository'}
                  </Button>
                ) : (
                  <Button
                    type="button"
                    onClick={handleNextStep}
                    disabled={isLoading}
                  >
                    Next
                  </Button>
                )}
              </div>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};