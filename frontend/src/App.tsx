import React, { useEffect, useState } from 'react';
import { Box, Container, useToast } from '@chakra-ui/react';
import { Navbar } from './components/Navbar';
import { StatsCards } from './components/StatsCards';
import { PipelineMonitor } from './components/PipelineMonitor';
import {
  fetchHealth,
  fetchStats,
  fetchRuns,
  HealthResponse,
  StatsResponse,
  PipelineRun,
} from './services/api';

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const toast = useToast();

  const loadData = async () => {
    try {
      setLoading(true);
      const [hData, sData, rData] = await Promise.all([
        fetchHealth(),
        fetchStats(),
        fetchRuns(),
      ]);
      setHealth(hData);
      setStats(sData);
      setRuns(rData);
    } catch (err: any) {
      toast({
        title: 'Erro ao carregar dados',
        description: err.message || 'Verifique se o backend FastAPI está em execução.',
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Polling cada 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <Box minH="100vh" bg="slate.50">
      <Navbar health={health} onRefresh={loadData} isLoading={loading} />
      <Container maxW="1400px" py={8}>
        <StatsCards stats={stats} />
        <PipelineMonitor runs={runs} />
      </Container>
    </Box>
  );
};

export default App;

