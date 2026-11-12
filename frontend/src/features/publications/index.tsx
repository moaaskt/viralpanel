import { useEffect, useState, useCallback } from 'react'
import {
  Share2,
  ExternalLink,
  Clock,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Video,
} from 'lucide-react'
import { toast } from 'sonner'
import { ViralHeader } from '@/components/layout/viral-header'
import { Main } from '@/components/layout/main'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  fetchHealth,
  fetchPublications,
  HealthResponse,
  Publication,
} from '@/services/api'

function InstagramIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
      <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
      <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
    </svg>
  )
}

function YoutubeIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M2.5 17a24.12 24.12 0 0 1 0-10 2 2 0 0 1 1.4-1.4 49.56 49.56 0 0 1 16.2 0A2 2 0 0 1 21.5 7a24.12 24.12 0 0 1 0 10 2 2 0 0 1-1.4 1.4 49.55 49.55 0 0 1-16.2 0A2 2 0 0 1 2.5 17" />
      <polygon points="10 15 15 12 10 9 10 15" fill="currentColor" />
    </svg>
  )
}

export function PublicationsPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [publications, setPublications] = useState<Publication[]>([])
  const [loading, setLoading] = useState(false)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [hData, pData] = await Promise.all([
        fetchHealth(),
        fetchPublications(50),
      ])
      setHealth(hData)
      setPublications(pData)
    } catch (err: any) {
      toast.error('Erro ao carregar publicações', {
        description: err.message,
      })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Solid, non-neon badge colors
  const getPlatformBadge = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'tiktok':
        return (
          <span className='inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold text-white bg-slate-900 dark:bg-slate-800'>
            <Video className='size-3' />
            TikTok
          </span>
        )
      case 'instagram':
        return (
          <span className='inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold text-white bg-fuchsia-800 dark:bg-fuchsia-900'>
            <InstagramIcon className='size-3' />
            Instagram Reels
          </span>
        )
      case 'youtube':
        return (
          <span className='inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold text-white bg-red-700 dark:bg-red-800'>
            <YoutubeIcon className='size-3' />
            YouTube Shorts
          </span>
        )
      default:
        return (
          <span className='inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-slate-800 bg-slate-200 dark:bg-slate-800 dark:text-slate-200'>
            {platform}
          </span>
        )
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'published':
        return (
          <span className='inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold text-white bg-emerald-700 dark:bg-emerald-800'>
            <CheckCircle2 className='size-3' />
            Publicado
          </span>
        )
      case 'scheduled':
        return (
          <span className='inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold text-white bg-blue-700 dark:bg-blue-800'>
            <Clock className='size-3' />
            Agendado
          </span>
        )
      case 'failed':
        return (
          <span className='inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold text-white bg-rose-700 dark:bg-rose-800'>
            <AlertCircle className='size-3' />
            Falha
          </span>
        )
      default:
        return (
          <span className='inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-slate-800 bg-slate-200 dark:bg-slate-800 dark:text-slate-200 capitalize'>
            {status}
          </span>
        )
    }
  }

  return (
    <>
      <ViralHeader
        title='Publicações Oficiais'
        subtitle='Histórico e agendamento de postagens em TikTok, Instagram Reels e YouTube Shorts'
        health={health}
        isLoading={loading}
        onRefresh={loadData}
      />

      <Main className='flex flex-col gap-6 p-4 sm:p-6 lg:p-8 max-w-[1600px] mx-auto w-full'>
        <Card className='rounded-xl border border-border/80 bg-card shadow-xs'>
          <CardHeader className='p-5 pb-3 border-b border-border/60'>
            <div className='flex items-center justify-between'>
              <div>
                <CardTitle className='text-sm font-bold uppercase tracking-wider text-foreground'>
                  Histórico de Postagens Oficiais
                </CardTitle>
                <CardDescription className='text-xs mt-0.5'>
                  Vídeos renderizados e transmitidos via endpoints oficiais dos parceiros
                </CardDescription>
              </div>
              <span className='inline-flex items-center px-2 py-0.5 rounded text-xs font-bold text-white bg-slate-900 dark:bg-slate-800'>
                {publications.length} {publications.length === 1 ? 'publicação' : 'publicações'}
              </span>
            </div>
          </CardHeader>
          <CardContent className='p-0'>
            {publications.length === 0 ? (
              <div className='flex flex-col items-center justify-center py-12 text-center text-muted-foreground px-4'>
                <Share2 className='size-10 opacity-30 mb-2' />
                <p className='text-sm font-semibold'>Nenhuma publicação registrada ainda.</p>
                <p className='text-xs mt-0.5'>
                  Após aprovação pelo Telegram, os vídeos renderizados são publicados automaticamente aqui.
                </p>
              </div>
            ) : (
              <div className='overflow-x-auto'>
                <Table>
                  <TableHeader className='bg-muted/25'>
                    <TableRow className='hover:bg-transparent border-b border-border/60'>
                      <TableHead className='text-xs font-bold text-foreground py-2.5 pl-5'>Plataforma</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5'>Status</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5'>Agendado Para</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5'>Publicado Em</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5'>Asset ID</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5 pr-5 text-right'>Link Oficial</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {publications.map((pub) => (
                      <TableRow key={pub.id} className='hover:bg-muted/40 transition-colors border-b border-border/40'>
                        <TableCell className='py-3 pl-4'>{getPlatformBadge(pub.platform)}</TableCell>
                        <TableCell className='py-3'>{getStatusBadge(pub.status)}</TableCell>
                        <TableCell className='text-xs text-muted-foreground whitespace-nowrap py-3'>
                          {pub.scheduled_for ? (
                            <div className='flex items-center gap-1.5'>
                              <Calendar className='size-3 text-muted-foreground' />
                              {new Date(pub.scheduled_for).toLocaleString('pt-BR')}
                            </div>
                          ) : (
                            '-'
                          )}
                        </TableCell>
                        <TableCell className='text-xs text-muted-foreground whitespace-nowrap py-3'>
                          {pub.published_at
                            ? new Date(pub.published_at).toLocaleString('pt-BR')
                            : '-'}
                        </TableCell>
                        <TableCell className='font-mono text-xs text-muted-foreground py-3'>
                          {pub.asset_id.slice(0, 8)}...
                        </TableCell>
                        <TableCell className='py-3 pr-4 text-right'>
                          {pub.url ? (
                            <Button
                              variant='outline'
                              size='sm'
                              asChild
                              className='h-7 px-2.5 gap-1 text-xs font-semibold border-border shadow-2xs hover:bg-accent'
                            >
                              <a
                                href={pub.url}
                                target='_blank'
                                rel='noopener noreferrer'
                              >
                                <ExternalLink className='size-3 text-foreground' />
                                Ver Post
                              </a>
                            </Button>
                          ) : (
                            <span className='text-xs text-muted-foreground italic'>
                              Aguardando link
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </Main>
    </>
  )
}
