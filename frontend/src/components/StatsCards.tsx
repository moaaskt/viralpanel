import React from 'react';
import { SimpleGrid, Card, CardBody, Stat, StatLabel, StatNumber, StatHelpText, HStack, Box } from '@chakra-ui/react';
import { Film, FileText, Share2, CheckCircle2 } from 'lucide-react';
import { StatsResponse } from '../services/api';

interface StatsCardsProps {
  stats: StatsResponse | null;
}

export const StatsCards: React.FC<StatsCardsProps> = ({ stats }) => {
  return (
    <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={5} mb={8}>
      <Card>
        <CardBody>
          <HStack justify="space-between" align="flex-start">
            <Stat>
              <StatLabel color="slate.500" fontSize="xs" textTransform="uppercase" fontWeight="600">
                Vídeos Minerados
              </StatLabel>
              <StatNumber fontSize="2xl" color="slate.900" mt={1}>
                {stats?.total_videos ?? 0}
              </StatNumber>
              <StatHelpText color="slate.500" mb={0}>
                Descobertos no TikTok
              </StatHelpText>
            </Stat>
            <Box p={2.5} bg="slate.100" color="slate.700" borderRadius="md">
              <Film size={20} />
            </Box>
          </HStack>
        </CardBody>
      </Card>

      <Card>
        <CardBody>
          <HStack justify="space-between" align="flex-start">
            <Stat>
              <StatLabel color="slate.500" fontSize="xs" textTransform="uppercase" fontWeight="600">
                Roteiros Criados
              </StatLabel>
              <StatNumber fontSize="2xl" color="slate.900" mt={1}>
                {stats?.total_scripts ?? 0}
              </StatNumber>
              <StatHelpText color="slate.500" mb={0}>
                Gerados com Gemini Flash
              </StatHelpText>
            </Stat>
            <Box p={2.5} bg="slate.100" color="slate.700" borderRadius="md">
              <FileText size={20} />
            </Box>
          </HStack>
        </CardBody>
      </Card>

      <Card>
        <CardBody>
          <HStack justify="space-between" align="flex-start">
            <Stat>
              <StatLabel color="slate.500" fontSize="xs" textTransform="uppercase" fontWeight="600">
                Publicações Concluídas
              </StatLabel>
              <StatNumber fontSize="2xl" color="slate.900" mt={1}>
                {stats?.total_publications ?? 0}
              </StatNumber>
              <StatHelpText color="slate.500" mb={0}>
                TikTok, Reels e Shorts
              </StatHelpText>
            </Stat>
            <Box p={2.5} bg="slate.100" color="slate.700" borderRadius="md">
              <Share2 size={20} />
            </Box>
          </HStack>
        </CardBody>
      </Card>

      <Card>
        <CardBody>
          <HStack justify="space-between" align="flex-start">
            <Stat>
              <StatLabel color="slate.500" fontSize="xs" textTransform="uppercase" fontWeight="600">
                Execuções Concluídas
              </StatLabel>
              <StatNumber fontSize="2xl" color="slate.900" mt={1}>
                {stats?.successful_runs ?? 0} / {stats?.total_runs ?? 0}
              </StatNumber>
              <StatHelpText color="slate.500" mb={0}>
                Taxa de sucesso da esteira
              </StatHelpText>
            </Stat>
            <Box p={2.5} bg="slate.100" color="slate.700" borderRadius="md">
              <CheckCircle2 size={20} />
            </Box>
          </HStack>
        </CardBody>
      </Card>
    </SimpleGrid>
  );
};

