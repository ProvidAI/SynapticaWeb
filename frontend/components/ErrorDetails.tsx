import React, { useState } from 'react';
import {
  AlertTriangle,
  Wifi,
  Clock,
  FileQuestion,
  Server,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Lightbulb
} from 'lucide-react';
import { Badge } from './ui/badge';
import { AlertWithIcon, AlertTitle, AlertDescription } from './ui/alert';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';

type ErrorType = 'connectivity' | 'timeout' | 'not_found' | 'http_error' | 'quality' | 'unknown';

interface ErrorDetailsProps {
  error: string;
  errorType?: ErrorType;
  rootCause?: string;
  troubleshooting?: string[];
  retryable?: boolean;
  className?: string;
}

const errorTypeConfig: Record<ErrorType, {
  icon: React.ElementType;
  label: string;
  variant: 'destructive' | 'warning' | 'info';
  badgeVariant: 'error' | 'warning' | 'info';
}> = {
  connectivity: {
    icon: Wifi,
    label: 'Connection Error',
    variant: 'destructive',
    badgeVariant: 'error',
  },
  timeout: {
    icon: Clock,
    label: 'Timeout',
    variant: 'warning',
    badgeVariant: 'warning',
  },
  not_found: {
    icon: FileQuestion,
    label: 'Not Found',
    variant: 'destructive',
    badgeVariant: 'error',
  },
  http_error: {
    icon: Server,
    label: 'Server Error',
    variant: 'destructive',
    badgeVariant: 'error',
  },
  quality: {
    icon: AlertCircle,
    label: 'Quality Issue',
    variant: 'warning',
    badgeVariant: 'warning',
  },
  unknown: {
    icon: AlertTriangle,
    label: 'Unknown Error',
    variant: 'destructive',
    badgeVariant: 'error',
  },
};

export function ErrorDetails({
  error,
  errorType = 'unknown',
  rootCause,
  troubleshooting = [],
  retryable = false,
  className = '',
}: ErrorDetailsProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const config = errorTypeConfig[errorType];
  const Icon = config.icon;

  return (
    <AlertWithIcon variant={config.variant} className={className}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <AlertTitle className="mb-0">Error During Execution</AlertTitle>
            <Badge variant={config.badgeVariant}>
              <Icon className="w-3 h-3 mr-1" />
              {config.label}
            </Badge>
            {retryable !== undefined && (
              <Badge variant={retryable ? 'info' : 'warning'}>
                {retryable ? 'Retryable' : 'Non-retryable'}
              </Badge>
            )}
          </div>

          <AlertDescription>
            <p className="font-medium text-sm mb-2">{error}</p>

            {rootCause && (
              <div className="mt-3 p-2 bg-black/5 dark:bg-white/5 rounded border border-current/10">
                <p className="text-xs font-semibold mb-1">Root Cause:</p>
                <p className="text-xs">{rootCause}</p>
              </div>
            )}

            {troubleshooting.length > 0 && (
              <Collapsible open={isExpanded} onOpenChange={setIsExpanded} className="mt-3">
                <CollapsibleTrigger className="flex items-center gap-2 text-xs font-semibold hover:underline">
                  <Lightbulb className="w-3.5 h-3.5" />
                  Troubleshooting Steps ({troubleshooting.length})
                  {isExpanded ? (
                    <ChevronUp className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5" />
                  )}
                </CollapsibleTrigger>

                <CollapsibleContent className="mt-2">
                  <ul className="space-y-1.5 pl-1">
                    {troubleshooting.map((step, index) => (
                      <li key={index} className="flex items-start gap-2 text-xs">
                        <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 opacity-60" />
                        <span>{step}</span>
                      </li>
                    ))}
                  </ul>
                </CollapsibleContent>
              </Collapsible>
            )}
          </AlertDescription>
        </div>
      </div>
    </AlertWithIcon>
  );
}
