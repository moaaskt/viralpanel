import React from 'react';
import {
  Box,
  Flex,
  Heading,
  HStack,
  Badge,
  Button,
  Text,
  useToast,
} from '@chakra-ui/react';
import { RefreshCw, Play, Activity } from 'lucide-react';
import { triggerPipeline, HealthResponse } from '../services/api';

interface NavbarProps {
  health: HealthResponse | null;
  onRefresh: () => void;
  isLoading: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ health, onRefresh, isLoading }) => {
  const [triggering, setTriggering] = React.useState(false);
  const toast = useToast();

  const handleManualTrigger = async () => {
    try {
      setTriggering(true);
      const res = await triggerPipeline();
      toast({
        title: 'Esteira Disparada!',
        description: `${res.message} (Task: ${res.task_id})`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      onRefresh();
    } catch (err: any) {
      toast({
        title: 'Erro ao disparar esteira',
        description: err.response?.data?.detail || err.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setTriggering(false);
    }
  };

  const isHealthy = health?.status === 'healthy';

  return (
    <Box bg="white" borderBottomWidth="1px" borderColor="slate.200" px={8} py={4}>
      <Flex align="center" justify="space-between" maxW="1400px" mx="auto">
        <HStack spacing={3}>
          <Box p={2} bg="slate.800" color="white" borderRadius="md">
            <Activity size={20} />
          </Box>
          <Box>
            <Heading size="md" color="slate.900" fontWeight="600" letterSpacing="-0.5px">
              ViralPanel
            </Heading>
            <Text fontSize="xs" color="slate.500">
              Pipeline Autônomo de Vídeos Curtos
            </Text>
          </Box>
        </HStack>

        <HStack spacing={4}>
          <HStack spacing={2} bg="slate.50" px={3} py={1.5} borderRadius="md" borderWidth="1px" borderColor="slate.200">
            <Text fontSize="xs" fontWeight="500" color="slate.600">
              Status Sistema:
            </Text>
            <Badge
              colorScheme={isHealthy ? 'green' : 'yellow'}
              variant="subtle"
              px={2}
              py={0.5}
              borderRadius="sm"
            >
              {health?.status || 'verificando...'}
            </Badge>
          </HStack>

          <Button
            leftIcon={<RefreshCw size={14} className={isLoading ? 'spin' : ''} />}
            variant="outline"
            size="sm"
            colorScheme="gray"
            onClick={onRefresh}
            isLoading={isLoading}
          >
            Atualizar
          </Button>

          <Button
            leftIcon={<Play size={14} />}
            size="sm"
            colorScheme="blue"
            bg="brand.500"
            _hover={{ bg: 'brand.600' }}
            onClick={handleManualTrigger}
            isLoading={triggering}
          >
            Disparar Esteira Diária
          </Button>
        </HStack>
      </Flex>
    </Box>
  );
};

