import {
  Box,
  Skeleton,
  CircularProgress,
  Typography,
  Alert,
} from '@mui/material';
import { memo } from 'react';
import { useTheme } from 'rj-core';

interface LoadingSkeletonProps {
  height?: number;
}

export const LoadingSkeleton = memo(
  ({ height = 400 }: LoadingSkeletonProps) => {
    const [theme] = useTheme();

    return (
      <Box
        display="flex"
        gap={2}
        mb={2}
      >
        <Box flex={1}>
          <Skeleton
            variant="rectangular"
            height={height}
            sx={{ borderRadius: 2 }}
          />
        </Box>
        <Box
          flex={2}
          bgcolor={theme === 'dark' ? '#1F1F20' : '#FFFFFF'}
          borderRadius={2}
          p={2}
        >
          <Skeleton
            variant="text"
            width="40%"
            height={32}
            sx={{ mb: 2 }}
          />
          <Skeleton
            variant="rectangular"
            height={60}
            sx={{ mb: 2, borderRadius: 2 }}
          />
          <Skeleton
            variant="rectangular"
            height={60}
            sx={{ mb: 2, borderRadius: 2 }}
          />
        </Box>
      </Box>
    );
  },
);

LoadingSkeleton.displayName = 'LoadingSkeleton';

interface LoadingSpinnerProps {
  message?: string;
  size?: number;
}

export const LoadingSpinner = memo(
  ({ message = 'Loading...', size = 24 }: LoadingSpinnerProps) => (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      p={2}
      gap={1}
    >
      <CircularProgress size={size} />
      {message && (
        <Typography
          variant="body2"
          color="textSecondary"
        >
          {message}
        </Typography>
      )}
    </Box>
  ),
);

LoadingSpinner.displayName = 'LoadingSpinner';

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export const ErrorMessage = memo(({ message, onRetry }: ErrorMessageProps) => (
  <Alert
    severity="error"
    action={
      onRetry && (
        <button
          onClick={onRetry}
          style={{ marginLeft: 8 }}
        >
          Retry
        </button>
      )
    }
  >
    {message}
  </Alert>
));

ErrorMessage.displayName = 'ErrorMessage';

interface EmptyStateProps {
  message: string;
  description?: string;
}

export const EmptyState = memo(({ message, description }: EmptyStateProps) => (
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
      color="textSecondary"
      gutterBottom
    >
      {message}
    </Typography>
    {description && (
      <Typography
        variant="body2"
        color="textSecondary"
      >
        {description}
      </Typography>
    )}
  </Box>
));

EmptyState.displayName = 'EmptyState';
