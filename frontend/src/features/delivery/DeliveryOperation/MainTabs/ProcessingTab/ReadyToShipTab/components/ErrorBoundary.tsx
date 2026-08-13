import { Box, Typography, Button } from '@mui/material';
import React, { Component, ReactNode } from 'react';
import { ToastTopHelper } from 'rj-core';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ReadyToShipTab Error:', error, errorInfo);
    ToastTopHelper.error('An unexpected error occurred');
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Box
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          p={4}
          textAlign="center"
        >
          <Typography
            variant="h6"
            color="error"
            gutterBottom
          >
            Something went wrong
          </Typography>
          <Typography
            variant="body2"
            color="textSecondary"
            mb={2}
          >
            {this.state.error?.message || 'An unexpected error occurred'}
          </Typography>
          <Button
            variant="outlined"
            onClick={this.handleRetry}
          >
            Try Again
          </Button>
        </Box>
      );
    }

    return this.props.children;
  }
}
