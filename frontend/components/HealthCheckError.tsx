import React from 'react';
import { Activity, XCircle, Terminal, Lightbulb } from 'lucide-react';
import { AlertWithIcon, AlertTitle, AlertDescription } from './ui/alert';
import { Badge } from './ui/badge';

interface HealthCheckErrorProps {
  message: string;
  error?: string;
  troubleshooting?: string[];
  className?: string;
}

export function HealthCheckError({
  message,
  error,
  troubleshooting = [],
  className = '',
}: HealthCheckErrorProps) {
  return (
    <AlertWithIcon variant="destructive" className={className}>
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <AlertTitle className="mb-0">System Health Check Failed</AlertTitle>
          <Badge variant="error">
            <Activity className="w-3 h-3 mr-1" />
            Pre-execution Check
          </Badge>
        </div>

        <AlertDescription>
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium mb-1">
                <XCircle className="w-4 h-4 inline mr-1 -mt-0.5" />
                {message}
              </p>
              {error && (
                <p className="text-xs mt-2 p-2 bg-black/10 dark:bg-white/10 rounded border border-current/10">
                  {error}
                </p>
              )}
            </div>

            {troubleshooting.length > 0 && (
              <div className="border-t border-current/20 pt-3">
                <div className="flex items-center gap-2 text-xs font-semibold mb-2">
                  <Lightbulb className="w-4 h-4" />
                  <span>Quick Fix Steps:</span>
                </div>
                <ul className="space-y-2">
                  {troubleshooting.map((step, index) => (
                    <li key={index} className="flex items-start gap-2 text-xs">
                      <Terminal className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 opacity-70" />
                      <code className="bg-black/10 dark:bg-white/10 px-1.5 py-0.5 rounded text-xs font-mono">
                        {step}
                      </code>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </AlertDescription>
      </div>
    </AlertWithIcon>
  );
}
