import React, { useEffect, useState } from 'react';
import {
  Box,
  Container,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  useToast,
  HStack,
  Text,
} from '@chakra-ui/react';
import { LayoutDashboard, Film, Share2 } from 'lucide-react';
import { Navbar } from './components/Navbar';
import { StatsCards } from './components/StatsCards';
import { PipelineMonitor } from './components/PipelineMonitor';
import { VideoLibrary } from './components/VideoLibrary';
import { PublicationHistory } from './components/PublicationHistory';
import {
  fetchHealth,
  fetchStats,
  fetchRuns,
  fetchVideos,
  fetchPublications,
  HealthResponse,
  StatsResponse,
  PipelineRun,
  SourceVideo,
  Publication,
} from './services/api';

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [videos, setVideos] = useState<SourceVideo[]>([]);
  const [publications, setPublications] = useState<Publication[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const toast = useToast();

  const loadData = async () => {
    try {
      setLoading(true);
      const [hData, sData, rData, vData, pData] = await Promise.all([
        fetchHealth(),
        fetchStats(),
        fetchRuns(),
        fetchVideos(),
        fetchPublications(),
      ]);
      setHealth(hData);
      setStats(sData);
      setRuns(rData);
      setVideos(vData);
      setPublications(pData);
    } catch (err: any) {
      toast({
        title: 'Erro ao conectar à API',
        description: err.message || 'Verifique se o backend FastAPI está em execução na porta 8000.',
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
    const interval = setInterval(loadData, 10000); // Polling a cada 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <Box minH="100vh" bg="slate.50">
      <Navbar health={health} onRefresh={loadData} isLoading={loading} />
      <Container maxW="1400px" py={8}>
        <StatsCards stats={stats} />

        <Tabs variant="enclosed" colorScheme="blue">
          <TabList mb={6} borderColor="slate.200">
            <Tab fontWeight="600" fontSize="sm" _selected={{ color: 'brand.600', borderColor: 'slate.200', borderBottomColor: 'white' }}>
              <HStack spacing={2}>
                <LayoutDashboard size={16} />
                <Text>Visão Geral & Esteira</Text>
              </HStack>
            </Tab>
            <Tab fontWeight="600" fontSize="sm" _selected={{ color: 'brand.600', borderColor: 'slate.200', borderBottomColor: 'white' }}>
              <HStack spacing={2}>
                <Film size={16} />
                <Text>Vídeos & Roteiros ({videos.length})</Text>
              </HStack>
            </Tab>
            <Tab fontWeight="600" fontSize="sm" _selected={{ color: 'brand.600', borderColor: 'slate.200', borderBottomColor: 'white' }}>
              <HStack spacing={2}>
                <Share2 size={16} />
                <Text>Publicações Oficiais ({publications.length})</Text>
              </HStack>
            </Tab>
          </TabList>

          <TabPanels>
            <TabPanel p={0}>
              <PipelineMonitor runs={runs} />
            </TabPanel>
            <TabPanel p={0}>
              <VideoLibrary videos={videos} />
            </TabPanel>
            <TabPanel p={0}>
              <PublicationHistory publications={publications} />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </Container>
    </Box>
  );
};

export default App;
