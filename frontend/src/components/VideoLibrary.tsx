import React, { useState } from 'react';
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
  Button,
  Box,
  HStack,
  Link,
  Tooltip,
} from '@chakra-ui/react';
import { ExternalLink, FileText, TrendingUp } from 'lucide-react';
import { SourceVideo, Script, fetchScripts } from '../services/api';
import { ScriptModal } from './ScriptModal';

interface VideoLibraryProps {
  videos: SourceVideo[];
}

export const VideoLibrary: React.FC<VideoLibraryProps> = ({ videos }) => {
  const [selectedScript, setSelectedScript] = useState<Script | null>(null);
  const [selectedTitle, setSelectedTitle] = useState<string>('');
  const [modalOpen, setModalOpen] = useState(false);
  const [loadingScriptId, setLoadingScriptId] = useState<string | null>(null);

  const handleOpenScript = async (video: SourceVideo) => {
    try {
      setLoadingScriptId(video.id);
      const scripts = await fetchScripts(video.id);
      if (scripts.length > 0) {
        setSelectedScript(scripts[0]);
      } else {
        setSelectedScript({
          id: 'mock-id',
          source_video_id: video.id,
          hook: 'Gancho pendente de processamento',
          script_text: 'Aguardando processamento do roteiro pelo Gemini Flash...',
          version: 1,
          created_at: new Date().toISOString(),
        });
      }
      setSelectedTitle(video.url);
      setModalOpen(true);
    } catch {
      // Fallback
      setSelectedScript(null);
    } finally {
      setLoadingScriptId(null);
    }
  };

  return (
    <Card mb={8}>
      <CardHeader pb={2}>
        <HStack justify="space-between">
          <Box>
            <Heading size="md" color="slate.900" fontWeight="600">
              Biblioteca de Vídeos Virais & Roteiros
            </Heading>
            <Text fontSize="sm" color="slate.500" mt={1}>
              Vídeos descobertos no TikTok com score de viralidade e roteiros gerados
            </Text>
          </Box>
        </HStack>
      </CardHeader>
      <CardBody pt={2}>
        {videos.length === 0 ? (
          <Box py={8} textAlign="center" color="slate.500">
            Nenhum vídeo coletado até o momento.
          </Box>
        ) : (
          <Box overflowX="auto">
            <Table variant="simple" size="sm">
              <Thead bg="slate.50">
                <Tr>
                  <Th color="slate.600">Origem / URL</Th>
                  <Th color="slate.600">Autor</Th>
                  <Th color="slate.600">Score Viral</Th>
                  <Th color="slate.600">Métricas</Th>
                  <Th color="slate.600">Status</Th>
                  <Th color="slate.600">Data Coleta</Th>
                  <Th color="slate.600" textAlign="right">Roteiro</Th>
                </Tr>
              </Thead>
              <Tbody>
                {videos.map((v) => (
                  <Tr key={v.id} _hover={{ bg: 'slate.50' }}>
                    <Td maxW="240px">
                      <Link
                        href={v.url}
                        isExternal
                        color="brand.600"
                        fontWeight="500"
                        fontSize="xs"
                        display="flex"
                        alignItems="center"
                        gap={1}
                      >
                        <Text isTruncated>{v.url}</Text>
                        <ExternalLink size={12} />
                      </Link>
                    </Td>
                    <Td fontSize="xs" color="slate.700">
                      {v.author || '@desconhecido'}
                    </Td>
                    <Td>
                      <HStack spacing={1}>
                        <TrendingUp size={12} color="#1D6FD8" />
                        <Text fontWeight="600" fontSize="xs" color="slate.900">
                          {v.score ? v.score.toFixed(1) : '-'}
                        </Text>
                      </HStack>
                    </Td>
                    <Td fontSize="xs" color="slate.600">
                      {v.metrics
                        ? `${(v.metrics.views || 0).toLocaleString()} views`
                        : '-'}
                    </Td>
                    <Td>
                      <Badge
                        colorScheme={v.status === 'selected' ? 'blue' : 'gray'}
                        variant="subtle"
                        fontSize="xs"
                        borderRadius="sm"
                      >
                        {v.status}
                      </Badge>
                    </Td>
                    <Td fontSize="xs" color="slate.600">
                      {new Date(v.collected_at).toLocaleDateString('pt-BR')}
                    </Td>
                    <Td textAlign="right">
                      <Tooltip label="Inspecionar Roteiro Gemini" placement="top">
                        <Button
                          size="xs"
                          leftIcon={<FileText size={12} />}
                          variant="outline"
                          colorScheme="blue"
                          onClick={() => handleOpenScript(v)}
                          isLoading={loadingScriptId === v.id}
                        >
                          Ver Roteiro
                        </Button>
                      </Tooltip>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        )}
      </CardBody>

      <ScriptModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        script={selectedScript}
        videoTitle={selectedTitle}
      />
    </Card>
  );
};

