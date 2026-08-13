import {
  Box,
  Button,
  Typography,
  Card,
  CardContent,
  Alert,
} from '@mui/material';
import React, { useState, useEffect } from 'react';

import {
  testIPDetection,
  getDetailedIPInfo,
  checkRealIP,
} from '@/utils/checkIP';

interface IPData {
  ip: string;
  country: string;
  city: string;
  region: string;
  isp: string;
  timezone: string;
  latitude: number | null;
  longitude: number | null;
}

const IPTestComponent: React.FC = () => {
  const [ipData, setIpData] = useState<IPData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);

  const testIPDetectionHandler = async () => {
    setLoading(true);
    setError(null);
    setTestResult(null);

    try {
      console.log('🧪 Starting IP Detection Test...');
      await testIPDetection();
      setTestResult(
        '✅ IP Detection test completed. Check browser console for details.',
      );
    } catch (err) {
      setError(
        '❌ IP Detection test failed. Check browser console for details.',
      );
    } finally {
      setLoading(false);
    }
  };

  const getDetailedIPInfoHandler = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await getDetailedIPInfo();

      if (result.success) {
        setIpData(result.data);
        console.log('📊 Detailed IP Info:', result.data);
      } else {
        setError(result.error || 'Failed to get IP info');
      }
    } catch (err) {
      setError('Error getting detailed IP info');
    } finally {
      setLoading(false);
    }
  };

  const clearCache = () => {
    localStorage.removeItem('cached_ip_data');
    localStorage.removeItem('cached_ip_time');
    setIpData(null);
    setError(null);
    setTestResult(null);
    console.log('🗑️ IP cache cleared');
  };

  useEffect(() => {
    // Auto-test on component mount
    testIPDetectionHandler();
  }, []);

  return (
    <Box sx={{ p: 2, maxWidth: 600 }}>
      <Typography
        variant="h5"
        gutterBottom
      >
        🌐 IP Detection Test
      </Typography>

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography
            variant="h6"
            gutterBottom
          >
            Test Controls
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              onClick={testIPDetectionHandler}
              disabled={loading}
            >
              {loading ? 'Testing...' : '🧪 Test IP Detection'}
            </Button>

            <Button
              variant="outlined"
              onClick={getDetailedIPInfoHandler}
              disabled={loading}
            >
              📊 Get Detailed IP Info
            </Button>

            <Button
              variant="outlined"
              color="secondary"
              onClick={clearCache}
            >
              🗑️ Clear Cache
            </Button>
          </Box>

          {testResult && (
            <Alert
              severity="info"
              sx={{ mb: 2 }}
            >
              {testResult}
            </Alert>
          )}

          {error && (
            <Alert
              severity="error"
              sx={{ mb: 2 }}
            >
              {error}
            </Alert>
          )}
        </CardContent>
      </Card>

      {ipData && (
        <Card>
          <CardContent>
            <Typography
              variant="h6"
              gutterBottom
            >
              📍 IP Information
            </Typography>

            <Box sx={{ display: 'grid', gap: 1 }}>
              <Typography>
                <strong>IP Address:</strong> {ipData.ip}
              </Typography>
              <Typography>
                <strong>Country:</strong> {ipData.country}
              </Typography>
              <Typography>
                <strong>City:</strong> {ipData.city}
              </Typography>
              <Typography>
                <strong>Region:</strong> {ipData.region}
              </Typography>
              <Typography>
                <strong>ISP:</strong> {ipData.isp}
              </Typography>
              <Typography>
                <strong>Timezone:</strong> {ipData.timezone}
              </Typography>
              {ipData.latitude && ipData.longitude && (
                <Typography>
                  <strong>Coordinates:</strong> {ipData.latitude},{' '}
                  {ipData.longitude}
                </Typography>
              )}
            </Box>
          </CardContent>
        </Card>
      )}

      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Typography
            variant="h6"
            gutterBottom
          >
            📋 Instructions
          </Typography>

          <Typography
            variant="body2"
            paragraph
          >
            1. Click "Test IP Detection" to run a comprehensive test
          </Typography>
          <Typography
            variant="body2"
            paragraph
          >
            2. Check browser console (F12) for detailed logs
          </Typography>
          <Typography
            variant="body2"
            paragraph
          >
            3. Use "Get Detailed IP Info" to see formatted IP data
          </Typography>
          <Typography
            variant="body2"
            paragraph
          >
            4. Clear cache if you want to force a fresh IP check
          </Typography>
          <Typography
            variant="body2"
            color="text.secondary"
          >
            💡 This helps verify if VPN is working by comparing IP location with
            browser geolocation
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default IPTestComponent;
