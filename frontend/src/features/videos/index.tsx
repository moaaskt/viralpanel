import { useEffect, useState, useCallback } from 'react'
import {
  Film,
  ExternalLink,
  FileText,
  TrendingUp,
  Sparkles,
  Loader2,
  Copy,
  Check,
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  fetchHealth,
  fetchVideos,
  fetchScripts,
  HealthResponse,
  SourceVideo,
  Script,
} from '@/services/api'

function formatNumber(num?: number | string) {
  if (num === undefined || num === null || num === '-') return '-'
  const n = typeof num === 'string' ? parseFloat(num) : num
  if (isNaN(n)) return String(num)
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toLocaleString('pt-BR')
}

export function VideosPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [videos, setVideos] = useState<SourceVideo[]>([])
  const [loading, setLoading] = useState(false)

  // Script dialog state
  const [selectedVideo, setSelectedVideo] = useState<SourceVideo | null>(null)
  const [script, setScript] = useState<Script | null>(null)
  const [scriptLoading, setScriptLoading] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [hData, vData] = await Promise.all([
        fetchHealth(),
        fetchVideos(50),
      ])
      setHealth(hData)
      setVideos(vData)
    } catch (err: any) {
      toast.error('Erro ao carregar vídeos minerados', {
        description: err.message,
      })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleOpenScript = async (video: SourceVideo) => {
    setSelectedVideo(video)
    setDialogOpen(true)
    setScriptLoading(true)
    setCopied(false)
    try {
      const scripts = await fetchScripts(video.id)
      if (scripts.length > 0) {
        setScript(scripts[0])
      } else {
        setScript({
          id: 'mock-pending',
          source_video_id: video.id,
          hook: 'Gancho ainda não processado pela esteira.',
          script_text:
            'Aguardando processamento e síntese do roteiro original pelo modelo Google Gemini 2.5 Flash...',
          version: 1,
          created_at: new Date().toISOString(),
        })
      }
    } catch (err: any) {
      toast.error('Erro ao buscar roteiro', {
        description: err.message,
      })
    } finally {
      setScriptLoading(false)
    }
  }

  const handleCopy = (text?: string) => {
    if (!text) return
    navigator.clipboard.writeText(text)
    setCopied(true)
    toast.success('Roteiro copiado para a área de transferência!')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <>
      <ViralHeader
        title='Mineração & Roteiros'
        subtitle='Vídeos virais coletados do TikTok e roteiros gerados via Gemini 2.5 Flash'
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
                  Acervo de Vídeos Descobertos
                </CardTitle>
                <CardDescription className='text-xs mt-0.5'>
                  Ordenados por Score Viral calculado pela taxa de engajamento do TikTok
                </CardDescription>
              </div>
              <span className='inline-flex items-center px-2 py-0.5 rounded text-xs font-bold text-white bg-slate-900 dark:bg-slate-800'>
                {videos.length} {videos.length === 1 ? 'vídeo' : 'vídeos'}
              </span>
            </div>
          </CardHeader>
          <CardContent className='p-0'>
            {videos.length === 0 ? (
              <div className='flex flex-col items-center justify-center py-12 text-center text-muted-foreground px-4'>
                <Film className='size-10 opacity-30 mb-2' />
                <p className='text-sm font-semibold'>Nenhum vídeo minerado disponível.</p>
                <p className='text-xs mt-0.5'>
                  Execute a esteira diária para minerar os conteúdos em alta no TikTok.
                </p>
              </div>
            ) : (
              <div className='overflow-x-auto'>
                <Table>
                  <TableHeader className='bg-muted/25'>
                    <TableRow className='hover:bg-transparent border-b border-border/60'>
                      <TableHead className='text-xs font-bold text-foreground py-2.5 pl-5'>Plataforma</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5'>Autor & Título</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5'>Score Viral</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5'>Métricas Estimadas</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5'>Coletado Em</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5'>Status</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5 pr-5 text-right'>Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {videos.map((vid) => {
                      const metrics = vid.metrics || {}
                      const views = formatNumber(metrics.views || metrics.play_count)
                      const likes = formatNumber(metrics.likes || metrics.digg_count)
                      const shares = formatNumber(metrics.shares || metrics.share_count)

                      return (
                        <TableRow key={vid.id} className='hover:bg-muted/40 transition-colors border-b border-border/40'>
                          <TableCell className='py-3 pl-4'>
                            <span className='inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-bold text-white bg-slate-900 dark:bg-slate-800 uppercase'>
                              <Video className='size-3' />
                              {vid.platform}
                            </span>
                          </TableCell>
                          <TableCell className='py-3 max-w-[280px]'>
                            <p className='font-bold text-xs text-foreground'>
                              {vid.author ? `@${vid.author}` : 'N/D'}
                            </p>
                            {metrics.title && (
                              <p className='text-muted-foreground truncate text-[11px] mt-0.5' title={metrics.title}>
                                {metrics.title}
                              </p>
                            )}
                          </TableCell>
                          <TableCell className='py-3 whitespace-nowrap'>
                            <span className='inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold text-white bg-indigo-700 dark:bg-indigo-800'>
                              <TrendingUp className='size-3' />
                              {vid.score ? vid.score.toFixed(1) : '-'}
                            </span>
                          </TableCell>
                          <TableCell className='text-xs text-muted-foreground py-3 whitespace-nowrap'>
                            <span>{views} views</span> • <span>{likes} likes</span>
                            {shares !== '-' && <span> • {shares} shares</span>}
                          </TableCell>
                          <TableCell className='text-xs text-muted-foreground whitespace-nowrap py-3'>
                            {new Date(vid.collected_at).toLocaleDateString('pt-BR')}
                          </TableCell>
                          <TableCell className='py-3'>
                            <span className='inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium text-slate-800 bg-slate-200 dark:bg-slate-800 dark:text-slate-200 capitalize'>
                              {vid.status}
                            </span>
                          </TableCell>
                          <TableCell className='py-3 pr-4 text-right'>
                            <div className='flex items-center justify-end gap-1.5'>
                              {vid.url && (
                                <Button
                                  variant='ghost'
                                  size='icon'
                                  className='size-7'
                                  asChild
                                  title='Abrir no TikTok'
                                >
                                  <a
                                    href={vid.url}
                                    target='_blank'
                                    rel='noopener noreferrer'
                                  >
                                    <ExternalLink className='size-3.5 text-muted-foreground' />
                                  </a>
                                </Button>
                              )}
                              <Button
                                variant='outline'
                                size='sm'
                                onClick={() => handleOpenScript(vid)}
                                className='h-7 px-2.5 gap-1.5 text-xs font-semibold border-border shadow-2xs hover:bg-accent'
                              >
                                <FileText className='size-3 text-foreground' />
                                Roteiro Gemini
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </Main>

      {/* Script Modal Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className='max-w-2xl border-border bg-card'>
          <DialogHeader className='border-b border-border pb-3'>
            <div className='flex items-center gap-2'>
              <div className='rounded bg-slate-900 text-white dark:bg-slate-800 p-1.5'>
                <Sparkles className='size-4' />
              </div>
              <DialogTitle className='text-base font-bold text-foreground'>
                Roteiro Original (Google Gemini 2.5 Flash)
              </DialogTitle>
            </div>
            <DialogDescription className='text-xs text-muted-foreground mt-1'>
              {selectedVideo?.author ? `Autor original: @${selectedVideo.author} • ` : ''}
              {script?.created_at
                ? `Gerado em ${new Date(script.created_at).toLocaleString('pt-BR')} (v${script.version})`
                : 'Processamento de roteiro'}
            </DialogDescription>
          </DialogHeader>

          {scriptLoading ? (
            <div className='flex flex-col items-center justify-center py-12 text-muted-foreground'>
              <Loader2 className='size-7 animate-spin mb-2 text-foreground' />
              <p className='text-xs font-medium'>Carregando roteiro do banco de dados...</p>
            </div>
          ) : (
            <div className='space-y-4 pt-3'>
              {/* Hook Section - Solid Left Border */}
              <div className='rounded-lg border-l-4 border-l-indigo-700 bg-muted/40 p-3.5 border-y border-r border-border'>
                <p className='text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1'>
                  Gancho de Retenção (Hook)
                </p>
                <p className='text-sm font-semibold text-foreground italic'>
                  "{script?.hook || 'Sem gancho definido.'}"
                </p>
              </div>

              {/* Full Script */}
              <div>
                <div className='flex items-center justify-between mb-1.5'>
                  <p className='text-[10px] font-bold text-muted-foreground uppercase tracking-wider'>
                    Roteiro Completo
                  </p>
                  <Button
                    variant='ghost'
                    size='sm'
                    onClick={() => handleCopy(script?.script_text)}
                    className='h-6 px-2 gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground'
                  >
                    {copied ? (
                      <>
                        <Check className='size-3 text-emerald-600' />
                        Copiado
                      </>
                    ) : (
                      <>
                        <Copy className='size-3' />
                        Copiar
                      </>
                    )}
                  </Button>
                </div>
                <ScrollArea className='h-56 rounded-md border border-border p-3.5 bg-background'>
                  <div className='whitespace-pre-wrap text-xs leading-relaxed text-foreground font-mono'>
                    {script?.script_text || 'Roteiro não disponível.'}
                  </div>
                </ScrollArea>
              </div>

              {/* Whisper Transcription (if available) */}
              {script?.transcription && (
                <div>
                  <p className='text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1'>
                    Transcrição do Áudio Original (Whisper)
                  </p>
                  <ScrollArea className='h-24 rounded-md border border-border p-2.5 bg-muted/20'>
                    <p className='text-[11px] text-muted-foreground whitespace-pre-wrap font-mono'>
                      {script.transcription}
                    </p>
                  </ScrollArea>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
