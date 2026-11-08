import { useEffect, useState, useCallback } from 'react'
import { Link } from '@tanstack/react-router'
import {
  Film,
  FileText,
  Share2,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
  Clock,
  ArrowRight,
  TrendingUp,
  Video,
  Sparkles,
  Zap,
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
  fetchStats,
  fetchRuns,
  fetchVideos,
  fetchScripts,
  HealthResponse,
  StatsResponse,
  PipelineRun,
  SourceVideo,
  Script,
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

function formatNumber(num?: number | string) {
  if (num === undefined || num === null || num === '-') return '-'
  const n = typeof num === 'string' ? parseFloat(num) : num
  if (isNaN(n)) return String(num)
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toLocaleString('pt-BR')
}

export function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [runs, setRuns] = useState<PipelineRun[]>([])
  const [videos, setVideos] = useState<SourceVideo[]>([])
  const [loading, setLoading] = useState(false)

  // Script preview modal
  const [selectedVideo, setSelectedVideo] = useState<SourceVideo | null>(null)
  const [script, setScript] = useState<Script | null>(null)
  const [scriptLoading, setScriptLoading] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [hData, sData, rData, vData] = await Promise.all([
        fetchHealth(),
        fetchStats(),
        fetchRuns(6),
        fetchVideos(5),
      ])
      setHealth(hData)
      setStats(sData)
      setRuns(rData)
      setVideos(vData)
    } catch (err: any) {
      toast.error('Erro ao conectar à API do ViralPanel', {
        description: err.message || 'Verifique se o backend FastAPI está em execução na porta 8000.',
      })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 10000)
    return () => clearInterval(interval)
  }, [loadData])

  const handleOpenScript = async (video: SourceVideo) => {
    setSelectedVideo(video)
    setDialogOpen(true)
    setScriptLoading(true)
    try {
      const scripts = await fetchScripts(video.id)
      if (scripts.length > 0) {
        setScript(scripts[0])
      } else {
        setScript({
          id: 'pending',
          source_video_id: video.id,
          hook: 'Gancho ainda não processado pela esteira.',
          script_text: 'Aguardando processamento e síntese do roteiro pelo modelo Google Gemini 2.5 Flash...',
          version: 1,
          created_at: new Date().toISOString(),
        })
      }
    } catch (err: any) {
      toast.error('Erro ao buscar roteiro', { description: err.message })
    } finally {
      setScriptLoading(false)
    }
  }

  // Solid, high-contrast, non-neon badge colors
  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
      case 'success':
        return (
          <span className='inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold text-white bg-emerald-700 dark:bg-emerald-800'>
            <CheckCircle2 className='size-3' />
            Concluído
          </span>
        )
      case 'running':
        return (
          <span className='inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold text-white bg-blue-700 dark:bg-blue-800 animate-pulse'>
            <PlayCircle className='size-3' />
            Em Andamento
          </span>
        )
      case 'failed':
        return (
          <span className='inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold text-white bg-rose-700 dark:bg-rose-800'>
            <AlertCircle className='size-3' />
            Falhou
          </span>
        )
      default:
        return (
          <span className='inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-slate-800 bg-slate-200 dark:bg-slate-800 dark:text-slate-200'>
            {status}
          </span>
        )
    }
  }

  const successRate =
    stats && stats.total_runs > 0
      ? Math.round((stats.successful_runs / stats.total_runs) * 100)
      : 0

  const tiktokCount = stats?.publications_by_platform?.['tiktok'] ?? 0
  const igCount = stats?.publications_by_platform?.['instagram'] ?? 0
  const ytCount = stats?.publications_by_platform?.['youtube'] ?? 0
  const totalPubs = stats?.total_publications || (tiktokCount + igCount + ytCount) || 0

  return (
    <>
      <ViralHeader
        title='Visão Geral'
        subtitle='Painel de controle e monitoramento autônomo do pipeline'
        health={health}
        isLoading={loading}
        onRefresh={loadData}
      />

      <Main className='flex flex-col gap-6 p-4 sm:p-6 lg:p-8 max-w-[1600px] mx-auto w-full'>
        {/* ROW 1: 4 Key Performance Metric Cards */}
        <div className='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5 lg:gap-6'>
          {/* Card 1: Vídeos Minerados */}
          <Card className='rounded-xl border border-border/80 bg-card shadow-xs transition-all duration-200 hover:shadow-sm'>
            <CardHeader className='flex flex-row items-center justify-between p-5 pb-2 space-y-0'>
              <span className='text-xs font-bold uppercase tracking-wider text-muted-foreground'>
                Vídeos Minerados
              </span>
              <div className='rounded-md bg-slate-100 dark:bg-slate-800 p-2 text-slate-700 dark:text-slate-300'>
                <Film className='size-4' />
              </div>
            </CardHeader>
            <CardContent className='p-5 pt-1'>
              <div className='text-3xl font-extrabold tracking-tight text-foreground'>
                {stats?.total_videos ?? 0}
              </div>
              <p className='mt-1 text-xs text-muted-foreground'>
                Coletados do TikTok por taxa de engajamento
              </p>
            </CardContent>
          </Card>

          {/* Card 2: Roteiros Criados */}
          <Card className='rounded-xl border border-border/80 bg-card shadow-xs transition-all duration-200 hover:shadow-sm'>
            <CardHeader className='flex flex-row items-center justify-between p-5 pb-2 space-y-0'>
              <span className='text-xs font-bold uppercase tracking-wider text-muted-foreground'>
                Roteiros Criados
              </span>
              <div className='rounded-md bg-slate-100 dark:bg-slate-800 p-2 text-slate-700 dark:text-slate-300'>
                <FileText className='size-4' />
              </div>
            </CardHeader>
            <CardContent className='p-5 pt-1'>
              <div className='text-3xl font-extrabold tracking-tight text-foreground'>
                {stats?.total_scripts ?? 0}
              </div>
              <p className='mt-1 text-xs text-muted-foreground'>
                Gerados com Google Gemini 2.5 Flash
              </p>
            </CardContent>
          </Card>

          {/* Card 3: Publicações Concluídas */}
          <Card className='rounded-xl border border-border/80 bg-card shadow-xs transition-all duration-200 hover:shadow-sm'>
            <CardHeader className='flex flex-row items-center justify-between p-5 pb-2 space-y-0'>
              <span className='text-xs font-bold uppercase tracking-wider text-muted-foreground'>
                Publicações Concluídas
              </span>
              <div className='rounded-md bg-slate-100 dark:bg-slate-800 p-2 text-slate-700 dark:text-slate-300'>
                <Share2 className='size-4' />
              </div>
            </CardHeader>
            <CardContent className='p-5 pt-1'>
              <div className='text-3xl font-extrabold tracking-tight text-foreground'>
                {stats?.total_publications ?? 0}
              </div>
              <p className='mt-1 text-xs text-muted-foreground'>
                TikTok, Instagram Reels e YouTube Shorts
              </p>
            </CardContent>
          </Card>

          {/* Card 4: Taxa de Sucesso */}
          <Card className='rounded-xl border border-border/80 bg-card shadow-xs transition-all duration-200 hover:shadow-sm'>
            <CardHeader className='flex flex-row items-center justify-between p-5 pb-2 space-y-0'>
              <span className='text-xs font-bold uppercase tracking-wider text-muted-foreground'>
                Taxa de Sucesso
              </span>
              <div className='rounded-md bg-emerald-700 text-white p-2 dark:bg-emerald-800'>
                <CheckCircle2 className='size-4' />
              </div>
            </CardHeader>
            <CardContent className='p-5 pt-1'>
              <div className='text-3xl font-extrabold tracking-tight text-foreground'>
                {successRate}%
              </div>
              <p className='mt-1 text-xs text-muted-foreground'>
                {stats?.successful_runs ?? 0} de {stats?.total_runs ?? 0} execuções concluídas
              </p>
            </CardContent>
          </Card>
        </div>

        {/* ROW 2: Distribution & Pipeline Operations */}
        <div className='grid gap-6 lg:grid-cols-12 items-stretch'>
          {/* Left Block (7 cols): Publicações por Rede */}
          <Card className='lg:col-span-7 rounded-xl border border-border/80 bg-card shadow-xs flex flex-col justify-between'>
            <CardHeader className='p-5 pb-4 border-b border-border/60'>
              <div className='flex items-center justify-between'>
                <div>
                  <CardTitle className='text-sm font-bold uppercase tracking-wider text-foreground'>
                    Publicações por Plataforma Oficial
                  </CardTitle>
                  <CardDescription className='text-xs mt-0.5'>
                    Distribuição dos vídeos distribuídos nas APIs sociais
                  </CardDescription>
                </div>
                <span className='inline-flex items-center px-2 py-0.5 rounded text-xs font-bold text-white bg-slate-900 dark:bg-slate-800'>
                  {totalPubs} no total
                </span>
              </div>
            </CardHeader>
            <CardContent className='p-5 space-y-3.5 flex-1 flex flex-col justify-around'>
              {/* TikTok Item */}
              <div className='flex items-center justify-between p-3.5 rounded-lg border border-border/60 bg-muted/20'>
                <div className='flex items-center gap-3'>
                  <div className='rounded-md p-2 bg-slate-900 text-white dark:bg-slate-800'>
                    <Video className='size-4' />
                  </div>
                  <div>
                    <div className='flex items-center gap-2'>
                      <p className='text-sm font-bold text-foreground'>TikTok</p>
                      <span className='inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold text-white bg-slate-900 dark:bg-slate-800'>
                        OFICIAL
                      </span>
                    </div>
                    <p className='text-xs text-muted-foreground'>Conta configurada via API</p>
                  </div>
                </div>
                <div className='text-right'>
                  <span className='text-xl font-extrabold text-foreground'>{tiktokCount}</span>
                  <p className='text-[11px] text-muted-foreground'>posts ativos</p>
                </div>
              </div>

              {/* Instagram Reels Item */}
              <div className='flex items-center justify-between p-3.5 rounded-lg border border-border/60 bg-muted/20'>
                <div className='flex items-center gap-3'>
                  <div className='rounded-md p-2 bg-fuchsia-800 text-white dark:bg-fuchsia-900'>
                    <InstagramIcon className='size-4' />
                  </div>
                  <div>
                    <div className='flex items-center gap-2'>
                      <p className='text-sm font-bold text-foreground'>Instagram Reels</p>
                      <span className='inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold text-white bg-fuchsia-800 dark:bg-fuchsia-900'>
                        META GRAPH API
                      </span>
                    </div>
                    <p className='text-xs text-muted-foreground'>Publicação direta no feed de Reels</p>
                  </div>
                </div>
                <div className='text-right'>
                  <span className='text-xl font-extrabold text-foreground'>{igCount}</span>
                  <p className='text-[11px] text-muted-foreground'>posts ativos</p>
                </div>
              </div>

              {/* YouTube Shorts Item */}
              <div className='flex items-center justify-between p-3.5 rounded-lg border border-border/60 bg-muted/20'>
                <div className='flex items-center gap-3'>
                  <div className='rounded-md p-2 bg-red-700 text-white dark:bg-red-800'>
                    <YoutubeIcon className='size-4' />
                  </div>
                  <div>
                    <div className='flex items-center gap-2'>
                      <p className='text-sm font-bold text-foreground'>YouTube Shorts</p>
                      <span className='inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold text-white bg-red-700 dark:bg-red-800'>
                        DATA API v3
                      </span>
                    </div>
                    <p className='text-xs text-muted-foreground'>Formato vertical 9:16 nativo</p>
                  </div>
                </div>
                <div className='text-right'>
                  <span className='text-xl font-extrabold text-foreground'>{ytCount}</span>
                  <p className='text-[11px] text-muted-foreground'>posts ativos</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Right Block (5 cols): Status Operacional da Automação */}
          <Card className='lg:col-span-5 rounded-xl border border-border/80 bg-card shadow-xs flex flex-col justify-between'>
            <CardHeader className='p-5 pb-4 border-b border-border/60'>
              <div className='flex items-center justify-between'>
                <CardTitle className='text-sm font-bold uppercase tracking-wider text-foreground'>
                  Fluxo Operacional Diário
                </CardTitle>
                <div className='rounded-md bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 p-1.5'>
                  <Zap className='size-3.5 fill-current' />
                </div>
              </div>
              <CardDescription className='text-xs mt-0.5'>
                Meta de produção diária do criador solo
              </CardDescription>
            </CardHeader>
            <CardContent className='p-5 space-y-4 flex-1 flex flex-col justify-between'>
              <div className='rounded-lg border border-border/70 bg-muted/30 p-4 space-y-2.5'>
                <div className='flex items-center justify-between text-xs'>
                  <span className='font-semibold text-foreground'>Meta de Produção Diária:</span>
                  <span className='font-bold text-foreground'>6 vídeos / dia</span>
                </div>
                <div className='h-2.5 w-full rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden'>
                  <div
                    className='h-full bg-emerald-700 dark:bg-emerald-600 transition-all rounded-full'
                    style={{
                      width: `${Math.min(100, ((stats?.total_scripts ?? 0) / 6) * 100)}%`,
                    }}
                  />
                </div>
                <p className='text-[11px] text-muted-foreground'>
                  {stats?.total_scripts ?? 0} vídeos processados hoje • Supervisão via Telegram
                </p>
              </div>

              <div className='space-y-2 text-xs'>
                <div className='flex items-center justify-between py-1.5 border-b border-border/40'>
                  <span className='text-muted-foreground'>LLM de Roteirização:</span>
                  <span className='font-bold text-foreground'>Gemini 2.5 Flash</span>
                </div>
                <div className='flex items-center justify-between py-1.5 border-b border-border/40'>
                  <span className='text-muted-foreground'>Clonagem de Voz & Avatar:</span>
                  <span className='font-bold text-foreground'>XTTS v2 + FFmpeg</span>
                </div>
                <div className='flex items-center justify-between py-1.5'>
                  <span className='text-muted-foreground'>Fila Assíncrona:</span>
                  <span className='inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold text-white bg-slate-800 dark:bg-slate-700'>
                    CELERY + REDIS
                  </span>
                </div>
              </div>
            </CardContent>
            <div className='p-5 pt-0'>
              <Button
                variant='outline'
                size='sm'
                asChild
                className='w-full text-xs font-semibold h-9 border-border hover:bg-accent'
              >
                <Link to='/pipeline'>
                  Ver Detalhes da Esteira
                  <ArrowRight className='size-3.5 ml-1.5' />
                </Link>
              </Button>
            </div>
          </Card>
        </div>

        {/* ROW 3: Side-by-Side Tables (Runs vs Videos) */}
        <div className='grid gap-6 lg:grid-cols-2 items-stretch'>
          {/* Table A: Últimas Execuções da Esteira */}
          <Card className='rounded-xl border border-border/80 bg-card shadow-xs flex flex-col'>
            <CardHeader className='flex flex-row items-center justify-between p-5 pb-3 border-b border-border/60'>
              <div>
                <CardTitle className='text-sm font-bold uppercase tracking-wider text-foreground'>
                  Monitor da Esteira (Runs Recentes)
                </CardTitle>
                <CardDescription className='text-xs mt-0.5'>
                  Status dos últimos disparos da fila Celery
                </CardDescription>
              </div>
              <Button variant='ghost' size='sm' asChild className='h-8 gap-1 text-xs font-semibold hover:bg-accent'>
                <Link to='/pipeline'>
                  Ver todos
                  <ArrowRight className='size-3.5' />
                </Link>
              </Button>
            </CardHeader>
            <CardContent className='p-0 flex-1 flex flex-col'>
              {runs.length === 0 ? (
                <div className='flex flex-1 flex-col items-center justify-center py-12 text-center text-muted-foreground px-4'>
                  <Clock className='size-8 opacity-30 mb-2' />
                  <p className='text-xs font-medium'>Nenhuma execução no banco ainda.</p>
                </div>
              ) : (
                <div className='overflow-x-auto flex-1'>
                  <Table>
                    <TableHeader className='bg-muted/25'>
                      <TableRow className='hover:bg-transparent border-b border-border/60'>
                        <TableHead className='text-xs font-bold text-foreground py-2.5 pl-5'>Início</TableHead>
                        <TableHead className='text-xs font-bold text-foreground py-2.5'>Estágio</TableHead>
                        <TableHead className='text-xs font-bold text-foreground py-2.5'>Status</TableHead>
                        <TableHead className='text-xs font-bold text-foreground py-2.5 pr-5 text-right'>Duração</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {runs.slice(0, 5).map((run) => (
                        <TableRow key={run.id} className='hover:bg-muted/40 transition-colors border-b border-border/40'>
                          <TableCell className='text-xs text-muted-foreground py-3 pl-5 whitespace-nowrap'>
                            {new Date(run.started_at).toLocaleTimeString('pt-BR', {
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit',
                            })} • {new Date(run.started_at).toLocaleDateString('pt-BR')}
                          </TableCell>
                          <TableCell className='py-3'>
                            <span className='inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700'>
                              {run.stage}
                            </span>
                          </TableCell>
                          <TableCell className='py-3'>
                            {getStatusBadge(run.status)}
                          </TableCell>
                          <TableCell className='text-xs text-muted-foreground py-3 pr-5 text-right font-mono whitespace-nowrap'>
                            {run.duration_seconds
                              ? `${run.duration_seconds.toFixed(1)}s`
                              : run.status === 'running'
                              ? 'calculando...'
                              : '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Table B: Vídeos Minerados no TikTok */}
          <Card className='rounded-xl border border-border/80 bg-card shadow-xs flex flex-col'>
            <CardHeader className='flex flex-row items-center justify-between p-5 pb-3 border-b border-border/60'>
              <div>
                <CardTitle className='text-sm font-bold uppercase tracking-wider text-foreground'>
                  Vídeos Minerados no TikTok
                </CardTitle>
                <CardDescription className='text-xs mt-0.5'>
                  Conteúdos em alta no nicho com maior score
                </CardDescription>
              </div>
              <Button variant='ghost' size='sm' asChild className='h-8 gap-1 text-xs font-semibold hover:bg-accent'>
                <Link to='/videos'>
                  Ver acervo
                  <ArrowRight className='size-3.5' />
                </Link>
              </Button>
            </CardHeader>
            <CardContent className='p-0 flex-1 flex flex-col'>
              {videos.length === 0 ? (
                <div className='flex flex-1 flex-col items-center justify-center py-12 text-center text-muted-foreground px-4'>
                  <Film className='size-8 opacity-30 mb-2' />
                  <p className='text-xs font-medium'>Nenhum vídeo minerado ainda.</p>
                </div>
              ) : (
                <div className='overflow-x-auto flex-1'>
                  <Table>
                    <TableHeader className='bg-muted/25'>
                      <TableRow className='hover:bg-transparent border-b border-border/60'>
                        <TableHead className='text-xs font-bold text-foreground py-2.5 pl-5'>Autor & Título</TableHead>
                        <TableHead className='text-xs font-bold text-foreground py-2.5'>Score</TableHead>
                        <TableHead className='text-xs font-bold text-foreground py-2.5'>Engajamento</TableHead>
                        <TableHead className='text-xs font-bold text-foreground py-2.5 pr-5 text-right'>Ação</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {videos.slice(0, 5).map((vid) => {
                        const metrics = vid.metrics || {}
                        const views = formatNumber(metrics.views || metrics.play_count)
                        const likes = formatNumber(metrics.likes || metrics.digg_count)

                        return (
                          <TableRow key={vid.id} className='hover:bg-muted/40 transition-colors border-b border-border/40'>
                            <TableCell className='py-3 pl-5 max-w-[200px]'>
                              <p className='text-xs font-bold text-foreground truncate'>
                                {vid.author ? `@${vid.author}` : 'N/D'}
                              </p>
                              {metrics.title && (
                                <p className='text-[11px] text-muted-foreground truncate'>
                                  {metrics.title}
                                </p>
                              )}
                            </TableCell>
                            <TableCell className='py-3 whitespace-nowrap'>
                              <span className='inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-bold text-white bg-indigo-700 dark:bg-indigo-800'>
                                <TrendingUp className='size-3' />
                                {vid.score ? vid.score.toFixed(1) : '-'}
                              </span>
                            </TableCell>
                            <TableCell className='text-xs text-muted-foreground py-3 whitespace-nowrap'>
                              <span>{views} views</span> • <span>{likes} likes</span>
                            </TableCell>
                            <TableCell className='py-3 pr-5 text-right'>
                              <Button
                                variant='outline'
                                size='sm'
                                onClick={() => handleOpenScript(vid)}
                                className='h-7 px-2.5 text-xs font-medium gap-1 border-border hover:bg-accent'
                              >
                                <FileText className='size-3' />
                                Roteiro
                              </Button>
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
        </div>
      </Main>

      {/* Script Preview Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className='max-w-2xl border-border bg-card'>
          <DialogHeader className='border-b border-border pb-3'>
            <div className='flex items-center gap-2'>
              <div className='rounded bg-slate-900 text-white dark:bg-slate-800 p-1.5'>
                <Sparkles className='size-4' />
              </div>
              <DialogTitle className='text-base font-bold text-foreground'>
                Roteiro Gerado (Google Gemini 2.5 Flash)
              </DialogTitle>
            </div>
            <DialogDescription className='text-xs text-muted-foreground mt-1'>
              {selectedVideo?.author ? `Autor original: @${selectedVideo.author} • ` : ''}
              {script?.created_at
                ? `Criado em ${new Date(script.created_at).toLocaleString('pt-BR')}`
                : 'Processamento de roteiro'}
            </DialogDescription>
          </DialogHeader>

          {scriptLoading ? (
            <div className='flex flex-col items-center justify-center py-10 text-muted-foreground'>
              <Clock className='size-6 animate-spin mb-2' />
              <p className='text-xs'>Buscando dados do roteiro...</p>
            </div>
          ) : (
            <div className='space-y-4 pt-3'>
              {/* Hook Box - Solid Border */}
              <div className='rounded-lg border-l-4 border-l-indigo-700 bg-muted/40 p-3.5 border-y border-r border-border'>
                <p className='text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1'>
                  Gancho de Retenção (Hook)
                </p>
                <p className='text-sm font-semibold text-foreground italic'>
                  "{script?.hook || 'Sem gancho definido.'}"
                </p>
              </div>

              {/* Script Text */}
              <div>
                <p className='text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5'>
                  Roteiro Completo
                </p>
                <ScrollArea className='h-56 rounded-md border border-border p-3.5 bg-background'>
                  <div className='whitespace-pre-wrap text-xs leading-relaxed text-foreground font-mono'>
                    {script?.script_text || 'Roteiro não disponível.'}
                  </div>
                </ScrollArea>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
