import React from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  Text,
  VStack,
  Box,
  Badge,
  HStack,
  Divider,
} from '@chakra-ui/react';
import { Script } from '../services/api';

interface ScriptModalProps {
  isOpen: boolean;
  onClose: () => void;
  script: Script | null;
  videoTitle?: string;
}

export const ScriptModal: React.FC<ScriptModalProps> = ({
  isOpen,
  onClose,
  script,
  videoTitle,
}) => {
  if (!script) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" isCentered>
      <ModalOverlay bg="blackAlpha.600" backdropFilter="blur(2px)" />
      <ModalContent borderRadius="lg" bg="white">
        <ModalHeader borderBottomWidth="1px" borderColor="slate.200" pb={3}>
          <HStack justify="space-between" align="center">
            <Box>
              <Text fontSize="lg" fontWeight="600" color="slate.900">
                Roteiro Gerado (Gemini 2.5 Flash)
              </Text>
              <Text fontSize="xs" color="slate.500" mt={0.5}>
                Versão v{script.version} • {new Date(script.created_at).toLocaleString('pt-BR')}
              </Text>
            </Box>
            <Badge colorScheme="blue" variant="subtle" px={2} py={0.5}>
              Original
            </Badge>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody py={5}>
          <VStack align="stretch" spacing={4}>
            {videoTitle && (
              <Box bg="slate.50" p={3} borderRadius="md" borderWidth="1px" borderColor="slate.200">
                <Text fontSize="xs" fontWeight="600" color="slate.600" textTransform="uppercase">
                  Vídeo Referência
                </Text>
                <Text fontSize="sm" color="slate.800" mt={0.5}>
                  {videoTitle}
                </Text>
              </Box>
            )}

            {script.hook && (
              <Box>
                <Badge colorScheme="purple" mb={1} fontSize="xs">
                  Gancho de Alta Retenção (0-3s)
                </Badge>
                <Box p={3} bg="purple.50" borderWidth="1px" borderColor="purple.200" borderRadius="md">
                  <Text fontSize="sm" fontWeight="600" color="purple.900">
                    "{script.hook}"
                  </Text>
                </Box>
              </Box>
            )}

            <Box>
              <Badge colorScheme="blue" mb={1} fontSize="xs">
                Conteúdo do Roteiro (Desenvolvimento e CTA)
              </Badge>
              <Box
                p={4}
                bg="slate.50"
                borderWidth="1px"
                borderColor="slate.200"
                borderRadius="md"
                whiteSpace="pre-wrap"
                fontFamily="sans-serif"
                fontSize="sm"
                color="slate.800"
                lineHeight="tall"
              >
                {script.script_text || 'Conteúdo textual do roteiro não disponível.'}
              </Box>
            </Box>

            {script.transcription && (
              <>
                <Divider />
                <Box>
                  <Text fontSize="xs" fontWeight="600" color="slate.500" textTransform="uppercase" mb={1}>
                    Transcrição Whisper Original
                  </Text>
                  <Box
                    p={3}
                    bg="slate.50"
                    borderRadius="md"
                    borderWidth="1px"
                    borderColor="slate.200"
                    fontSize="xs"
                    color="slate.600"
                    maxH="120px"
                    overflowY="auto"
                  >
                    {script.transcription}
                  </Box>
                </Box>
              </>
            )}
          </VStack>
        </ModalBody>

        <ModalFooter borderTopWidth="1px" borderColor="slate.200" pt={3}>
          <Button variant="outline" size="sm" onClick={onClose}>
            Fechar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
