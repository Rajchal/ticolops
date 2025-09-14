import React, { useState, useEffect } from 'react';
import { X, ExternalLink, RefreshCw, Smartphone, Tablet, Monitor, AlertCircle, Share2, Copy, Check } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import type { Deployment } from './DeploymentCard';

interface PreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  deployment: Deployment | null;
}

type ViewportSize = 'mobile' | 'tablet' | 'desktop';

const VIEWPORT_SIZES = {
  mobile: { width: 375, height: 667, label: 'Mobile', icon: Smartphone },
  tablet: { width: 768, height: 1024, label: 'Tablet', icon: Tablet },
  desktop: { width: 1200, height: 800, label: 'Desktop', icon: Monitor },
};

export const PreviewModal: React.FC<PreviewModalProps> = ({
  isOpen,
  onClose,
  deployment,
}) => {
  const [viewport, setViewport] = useState<ViewportSize>('desktop');
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [copied, setCopied] = useState(false);

  const previewUrl = deployment?.url || deployment?.previewUrl;

  useEffect(() => {
    if (isOpen && previewUrl) {
      setIsLoading(true);
      setHasError(false);
    }
  }, [isOpen, previewUrl]);

  const handleIframeLoad = () => {
    setIsLoading(false);
    setHasError(false);
  };

  const handleIframeError = () => {
    setIsLoading(false);
    setHasError(true);
  };

  const handleCopyUrl = async () => {
    if (!previewUrl) return;
    
    try {
      await navigator.clipboard.writeText(previewUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy URL:', error);
    }
  };

  const handleOpenInNewTab = () => {
    if (previewUrl) {
      window.open(previewUrl, '_blank');
    }
  };

  const handleRefresh = () => {
    setIsLoading(true);
    setHasError(false);
    // Force iframe reload by updating its key
    const iframe = document.getElementById('preview-iframe') as HTMLIFrameElement;
    if (iframe) {
      iframe.src = iframe.src;
    }
  };

  if (!isOpen || !deployment || !previewUrl) return null;

  const currentViewport = VIEWPORT_SIZES[viewport];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-7xl h-[90vh] flex flex-col">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b">
          <div>
            <CardTitle className="text-xl font-semibold">Preview</CardTitle>
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
              {/* Viewport Size Selector */}
              <div className="flex items-center space-x-2">
                {Object.entries(VIEWPORT_SIZES).map(([key, config]) => {
                  const Icon = config.icon;
                  return (
                    <Button
                      key={key}
                      variant={viewport === key ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setViewport(key as ViewportSize)}
                      className="flex items-center space-x-1"
                    >
                      <Icon className="h-4 w-4" />
                      <span className="hidden sm:inline">{config.label}</span>
                    </Button>
                  );
                })}
              </div>
              
              <div className="text-sm text-muted-foreground">
                {currentViewport.width} × {currentViewport.height}
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <div className="text-sm text-muted-foreground font-mono bg-gray-100 px-2 py-1 rounded max-w-xs truncate">
                {previewUrl}
              </div>
              
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyUrl}
              >
                {copied ? (
                  <Check className="h-4 w-4 mr-2 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4 mr-2" />
                )}
                {copied ? 'Copied!' : 'Copy URL'}
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={isLoading}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={handleOpenInNewTab}
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Open in New Tab
              </Button>
            </div>
          </div>

          {/* Preview Container */}
          <div className="flex-1 flex items-center justify-center bg-gray-100 p-8">
            <div 
              className="bg-white rounded-lg shadow-lg overflow-hidden relative"
              style={{
                width: Math.min(currentViewport.width, window.innerWidth - 200),
                height: Math.min(currentViewport.height, window.innerHeight - 300),
              }}
            >
              {/* Loading Overlay */}
              {isLoading && (
                <div className="absolute inset-0 bg-white bg-opacity-90 flex items-center justify-center z-10">
                  <div className="text-center">
                    <RefreshCw className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground">Loading preview...</p>
                  </div>
                </div>
              )}

              {/* Error State */}
              {hasError && !isLoading && (
                <div className="absolute inset-0 bg-white flex items-center justify-center z-10">
                  <div className="text-center p-8">
                    <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Failed to Load Preview</h3>
                    <p className="text-sm text-gray-600 mb-4">
                      The preview could not be loaded. This might be due to:
                    </p>
                    <ul className="text-sm text-gray-600 text-left mb-4 space-y-1">
                      <li>• The deployment is still in progress</li>
                      <li>• The application has errors</li>
                      <li>• Network connectivity issues</li>
                      <li>• CORS restrictions</li>
                    </ul>
                    <div className="space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRefresh}
                      >
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Try Again
                      </Button>
                      <Button
                        variant="default"
                        size="sm"
                        onClick={handleOpenInNewTab}
                      >
                        <ExternalLink className="h-4 w-4 mr-2" />
                        Open Directly
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {/* Preview Iframe */}
              <iframe
                id="preview-iframe"
                src={previewUrl}
                className="w-full h-full border-0"
                onLoad={handleIframeLoad}
                onError={handleIframeError}
                sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
                title={`Preview of ${deployment.repositoryName}`}
              />
            </div>
          </div>

          {/* Status Bar */}
          <div className="flex items-center justify-between p-3 border-t bg-gray-50 text-sm text-muted-foreground">
            <div className="flex items-center space-x-4">
              <span>Deployment: {deployment.status}</span>
              {deployment.completedAt && (
                <span>
                  Deployed {new Date(deployment.completedAt).toLocaleString()}
                </span>
              )}
              {deployment.buildDuration && (
                <span>
                  Build time: {Math.floor(deployment.buildDuration / 60)}m {deployment.buildDuration % 60}s
                </span>
              )}
            </div>
            
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (navigator.share && previewUrl) {
                    navigator.share({
                      title: `Preview: ${deployment.repositoryName}`,
                      url: previewUrl,
                    });
                  } else {
                    handleCopyUrl();
                  }
                }}
                className="text-xs"
              >
                <Share2 className="h-3 w-3 mr-1" />
                Share
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};