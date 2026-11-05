import React from 'react';
import {
  Card,
  CardHeader,
  CardBody,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Text,
  HStack,
  Box,
} from '@chakra-ui/react';
import { Clock, CheckCircle, AlertCircle, PlayCircle } from 'lucide-react';
import { PipelineRun } from '../services/api';

interface PipelineMonitorProps {
  runs: PipelineRun[];
}

export const PipelineMonitor: React.FC<PipelineMonitorProps> = ({ runs }) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <Badge colorScheme="green" variant="subtle" px={2} py={0.5} borderRadius="sm">
            <HStack spacing={1}>
              <CheckCircle size={12} />
              <span>Concluído</span>
            </HStack>
          </Badge>
        );
      case 'running':
        return (
          <Badge colorScheme="blue" variant="subtle" px={2} py={0.5} borderRadius="sm">
            <HStack spacing={1}>
              <PlayCircle size={12} />
              <span>Em Andamento</span>
            </HStack>
          </Badge>
        );
      case 'failed':
        return (
          <Badge colorScheme="red" variant="subtle" px={2} py={0.5} borderRadius="sm">
            <HStack spacing={1}>
              <AlertCircle size={12} />
              <span>Falhou</span>
            </HStack>
          </Badge>
        );
      default:
        return (
          <Badge colorScheme="gray" variant="subtle" px={2} py={0.5} borderRadius="sm">
            <HStack spacing={1}>
              <Clock size={12} />
              <span>{status}</span>
            </HStack>
          </Badge>
        );
    }
  };

  return (
    <Card mb={8}>
      <CardHeader pb={2}>
        <HStack justify="space-between">
          <Box>
            <Heading size="md" color="slate.900" fontWeight="600">
              Monitor da Esteira Diária
            </Heading>
            <Text fontSize="sm" color="slate.500" mt={1}>
              Status das tarefas assíncronas do Celery e etapas da esteira
            </Text>
          </Box>
        </HStack>
      </CardHeader>
      <CardBody pt={2}>
        {runs.length === 0 ? (
          <Box py={8} textAlign="center" color="slate.500">
            Nenhuma execução registrada no histórico recente.
          </Box>
        ) : (
          <Box overflowX="auto">
            <Table variant="simple" size="sm">
              <Thead bg="slate.50">
                <Tr>
                  <Th color="slate.600">ID da Execução</Th>
                  <Th color="slate.600">Iniciado Em</Th>
                  <Th color="slate.600">Etapa Atual</Th>
                  <Th color="slate.600">Status</Th>
                  <Th color="slate.600">Duração</Th>
                  <Th color="slate.600">Mensagem / Erro</Th>
                </Tr>
              </Thead>
              <Tbody>
                {runs.map((run) => (
                  <Tr key={run.id} _hover={{ bg: 'slate.50' }}>
                    <Td fontWeight="500" color="slate.800" fontFamily="mono" fontSize="xs">
                      {run.id.slice(0, 8)}...
                    </Td>
                    <Td color="slate.600">
                      {new Date(run.started_at).toLocaleString('pt-BR')}
                    </Td>
                    <Td>
                      <Badge variant="outline" colorScheme="gray" textTransform="uppercase" fontSize="xs">
                        {run.stage}
                      </Badge>
                    </Td>
                    <Td>{getStatusBadge(run.status)}</Td>
                    <Td color="slate.600">
                      {run.duration_seconds ? `${run.duration_seconds.toFixed(1)}s` : '-'}
                    </Td>
                    <Td color={run.error_message ? 'red.600' : 'slate.500'} fontSize="xs" maxW="280px" isTruncated>
                      {run.error_message || 'Nenhum erro registrado'}
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        )}
      </CardBody>
    </Card>
  );
};

