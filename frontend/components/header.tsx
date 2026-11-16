"use client";

import { useEffect, useState } from 'react';
import { Activity, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { ConnectionStatus } from '@/lib/types';

export function Header() {
  const [status, setStatus] = useState<ConnectionStatus>('checking');

  useEffect(() => {
    const checkConnection = async () => {
      try {
        await apiClient.healthCheck();
        setStatus('connected');
      } catch {
        setStatus('disconnected');
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = () => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'disconnected':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'checking':
        return <Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'connected':
        return 'Connected';
      case 'disconnected':
        return 'Disconnected';
      case 'checking':
        return 'Checking...';
    }
  };

  return (
    <header className="border-b bg-background">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Activity className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-semibold">HireLens</h1>
          </div>
          <span className="text-sm text-muted-foreground">AI-powered resume screening</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          {getStatusIcon()}
          <span className={status === 'connected' ? 'text-green-600' : status === 'disconnected' ? 'text-red-600' : 'text-muted-foreground'}>
            {getStatusText()}
          </span>
        </div>
      </div>
    </header>
  );
}
