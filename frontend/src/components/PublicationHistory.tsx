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
  Box,
  HStack,
  Link,
} from '@chakra-ui/react';
import { ExternalLink, CheckCircle, Clock } from 'lucide-react';
import { Publication } from '../services/api';

interface PublicationHistoryProps {
  publications: Publication[];
}

export const PublicationHistory: React.FC<PublicationHistoryProps> = ({
  publications,
}) => {
  const getPlatformBadge = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'tiktok':
        return (
          <Badge bg="slate.800" color="white" px={2} py={0.5} borderRadius="sm" fontSize="xs">
            TikTok
          </Badge>
        );
      case 'instagram':
        return (
          <Badge bg="purple.700" color="white" px={2} py={0.5} borderRadius="sm" fontSize="xs">
            Instagram Reels
          </Badge>
        );
      case 'youtube':
        return (
          <Badge bg="red.700" color="white" px={2} py={0.5} borderRadius="sm" fontSize="xs">
            YouTube Shorts
          </Badge>
        );
      default:
        return (
          <Badge variant="subtle" colorScheme="gray" fontSize="xs">
            {platform}
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
              Histórico de Publicações Oficiais
            </Heading>
            <Text fontSize="sm" color="slate.500" mt={1}>
              Postagens agendadas e confirmadas via TikTok, Meta Graph API e YouTube Data API
            </Text>
          </Box>
        </HStack>
      </CardHeader>
      <CardBody pt={2}>
        {publications.length === 0 ? (
          <Box py={8} textAlign="center" color="slate.500">
            Nenhuma publicação realizada ou agendada até o momento.
          </Box>
        ) : (
          <Box overflowX="auto">
            <Table variant="simple" size="sm">
              <Thead bg="slate.50">
                <Tr>
                  <Th color="slate.600">Plataforma</Th>
                  <Th color="slate.600">Status</Th>
                  <Th color="slate.600">Publicado Em</Th>
                  <Th color="slate.600">Agendamento</Th>
                  <Th color="slate.600">Link / Referência</Th>
                </Tr>
              </Thead>
              <Tbody>
                {publications.map((pub) => (
                  <Tr key={pub.id} _hover={{ bg: 'slate.50' }}>
                    <Td>{getPlatformBadge(pub.platform)}</Td>
                    <Td>
                      {pub.status === 'published' ? (
                        <Badge colorScheme="green" variant="subtle" px={2} py={0.5}>
                          <HStack spacing={1}>
                            <CheckCircle size={10} />
                            <span>Publicado</span>
                          </HStack>
                        </Badge>
                      ) : (
                        <Badge colorScheme="yellow" variant="subtle" px={2} py={0.5}>
                          <HStack spacing={1}>
                            <Clock size={10} />
                            <span>{pub.status}</span>
                          </HStack>
                        </Badge>
                      )}
                    </Td>
                    <Td fontSize="xs" color="slate.600">
                      {pub.published_at
                        ? new Date(pub.published_at).toLocaleString('pt-BR')
                        : '-'}
                    </Td>
                    <Td fontSize="xs" color="slate.600">
                      {pub.scheduled_for
                        ? new Date(pub.scheduled_for).toLocaleString('pt-BR')
                        : 'Imediato'}
                    </Td>
                    <Td fontSize="xs">
                      {pub.url ? (
                        <Link
                          href={pub.url}
                          isExternal
                          color="brand.600"
                          fontWeight="500"
                          display="flex"
                          alignItems="center"
                          gap={1}
                        >
                          <span>Ver Publicação</span>
                          <ExternalLink size={12} />
                        </Link>
                      ) : (
                        <Text color="slate.400">-</Text>
                      )}
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
