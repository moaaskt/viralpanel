import { useEffect, useState, useCallback } from 'react'
import {
  Clock,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
  Activity,
  Layers,
  Bot,
  Mic,
  Send,
  Video,
  Copy,
  Check,
  Terminal,
  FileCode,
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
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
  fetchRuns,
  HealthResponse,
  PipelineRun,
} from '@/services/api'

export function PipelinePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [runs, setRuns] = useState<PipelineRun[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedRun, setSelectedRun] = useState<PipelineRun | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleOpenDiagnostic = (run: PipelineRun) => {
    setSelectedRun(run)
    setDialogOpen(true)
    setCopied(false)
  }

  const handleCopy = (text?: string) => {
    if (!text) return
    navigator.clipboard.writeText(text)
    setCopied(true)
    toast.success('Log de diagnóstico copiado!')
    setTimeout(() => setCopied(false), 2000)
  }

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [hData, rData] = await Promise.all([
        fetchHealth(),
        fetchRuns(50),
      ])
      setHealth(hData)
      setRuns(rData)
    } catch (err: any) {
      toast.error('Erro ao carregar execuções da esteira', {
        description: err.message,
      })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 8000)
    return () => clearInterval(interval)
  }, [loadData])

  // Solid, non-neon badge colors
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

  const getStageBadge = (stage: string) => {
    return (
      <span className='inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 capitalize'>
        {stage}
      </span>
    )
  }

  return (
    <>
      <ViralHeader
        title='Esteira de Produção'
        subtitle='Monitoramento detalhado dos estágios e tarefas em fila Celery'
        health={health}
        isLoading={loading}
        onRefresh={loadData}
      />

      <Main className='flex flex-col gap-6 p-4 sm:p-6 lg:p-8 max-w-[1600px] mx-auto w-full'>
        {/* Unified Pipeline Workflow Stepper Card */}
        <Card className='rounded-xl border border-border/80 bg-card shadow-xs overflow-hidden'>
          <CardHeader className='p-5 pb-3 border-b border-border/60 bg-muted/20'>
            <div className='flex items-center justify-between'>
              <div>
                <CardTitle className='text-xs font-bold uppercase tracking-wider text-foreground'>
                  Ciclo Completo da Esteira Autônoma
                </CardTitle>
                <CardDescription className='text-xs mt-0.5'>
                  Fluxo linear de produção executado automaticamente pelo Celery Worker
                </CardDescription>
              </div>
              <span className='inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold text-white bg-slate-900 dark:bg-slate-800'>
                5 ETAPAS
              </span>
            </div>
          </CardHeader>
          <CardContent className='p-5'>
            <div className='grid gap-3.5 sm:grid-cols-2 lg:grid-cols-5'>
              {/* Step 1 */}
              <div className='flex flex-col p-3 rounded-lg border border-border/70 bg-card shadow-2xs relative'>
                <div className='flex items-center justify-between mb-2'>
                  <span className='size-5 rounded-full bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 text-[11px] font-bold flex items-center justify-center'>
                    1
                  </span>
                  <div className='rounded p-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'>
                    <Video className='size-3.5' />
                  </div>
                </div>
                <h4 className='text-xs font-bold text-foreground'>Discovery</h4>
                <p className='text-[11px] text-muted-foreground mt-0.5'>
                  Mineração de tendências e transcrição Whisper
                </p>
              </div>

              {/* Step 2 */}
              <div className='flex flex-col p-3 rounded-lg border border-border/70 bg-card shadow-2xs relative'>
                <div className='flex items-center justify-between mb-2'>
                  <span className='size-5 rounded-full bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 text-[11px] font-bold flex items-center justify-center'>
                    2
                  </span>
                  <div className='rounded p-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'>
                    <Bot className='size-3.5' />
                  </div>
                </div>
                <h4 className='text-xs font-bold text-foreground'>Scripting</h4>
                <p className='text-[11px] text-muted-foreground mt-0.5'>
                  Geração de gancho e roteiro via Gemini Flash
                </p>
              </div>

              {/* Step 3 */}
              <div className='flex flex-col p-3 rounded-lg border border-border/70 bg-card shadow-2xs relative'>
                <div className='flex items-center justify-between mb-2'>
                  <span className='size-5 rounded-full bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 text-[11px] font-bold flex items-center justify-center'>
                    3
                  </span>
                  <div className='rounded p-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'>
                    <Mic className='size-3.5' />
                  </div>
                </div>
                <h4 className='text-xs font-bold text-foreground'>Studio & Render</h4>
                <p className='text-[11px] text-muted-foreground mt-0.5'>
                  Voz XTTS v2, avatar e composição FFmpeg 9:16
                </p>
              </div>

              {/* Step 4 */}
              <div className='flex flex-col p-3 rounded-lg border border-border/70 bg-card shadow-2xs relative'>
                <div className='flex items-center justify-between mb-2'>
                  <span className='size-5 rounded-full bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 text-[11px] font-bold flex items-center justify-center'>
                    4
                  </span>
                  <div className='rounded p-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'>
                    <Send className='size-3.5' />
                  </div>
                </div>
                <h4 className='text-xs font-bold text-foreground'>Supervisão</h4>
                <p className='text-[11px] text-muted-foreground mt-0.5'>
                  Notificação e botões de aprovação no Telegram
                </p>
              </div>

              {/* Step 5 */}
              <div className='flex flex-col p-3 rounded-lg border border-border/70 bg-card shadow-2xs relative'>
                <div className='flex items-center justify-between mb-2'>
                  <span className='size-5 rounded-full bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 text-[11px] font-bold flex items-center justify-center'>
                    5
                  </span>
                  <div className='rounded p-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'>
                    <Layers className='size-3.5' />
                  </div>
                </div>
                <h4 className='text-xs font-bold text-foreground'>Publicação</h4>
                <p className='text-[11px] text-muted-foreground mt-0.5'>
                  Postagem automática nas APIs oficiais
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Runs History Table */}
        <Card className='rounded-xl border border-border/80 bg-card shadow-xs'>
          <CardHeader className='p-5 pb-3 border-b border-border/60'>
            <div className='flex items-center justify-between'>
              <div>
                <CardTitle className='text-sm font-bold uppercase tracking-wider text-foreground'>
                  Histórico de Execuções da Esteira
                </CardTitle>
                <CardDescription className='text-xs mt-0.5'>
                  Registros individuais das tarefas executadas pelo pipeline
                </CardDescription>
              </div>
              <span className='inline-flex items-center px-2 py-0.5 rounded text-xs font-bold text-white bg-slate-900 dark:bg-slate-800'>
                {runs.length} {runs.length === 1 ? 'execução' : 'execuções'}
              </span>
            </div>
          </CardHeader>
          <CardContent className='p-0'>
            {runs.length === 0 ? (
              <div className='flex flex-col items-center justify-center py-12 text-center text-muted-foreground px-4'>
                <Activity className='size-10 opacity-30 mb-2' />
                <p className='text-sm font-semibold'>Nenhuma execução no banco de dados.</p>
                <p className='text-xs mt-0.5'>
                  Clique em "Disparar Esteira" no topo para rodar o pipeline diário.
                </p>
              </div>
            ) : (
              <div className='overflow-x-auto'>
                <Table>
                  <TableHeader className='bg-muted/25'>
                    <TableRow className='hover:bg-transparent border-b border-border/60'>
                      <TableHead className='text-xs font-bold text-foreground py-2.5 pl-5 w-[110px]'>ID</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5 w-[180px]'>Início</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5 w-[130px]'>Estágio</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5 w-[140px]'>Status</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5 w-[100px]'>Duração</TableHead>
                      <TableHead className='text-xs font-bold text-foreground py-2.5 pr-5'>Diagnóstico / Observações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {runs.map((run) => (
                      <TableRow key={run.id} className='hover:bg-muted/40 transition-colors border-b border-border/40'>
                        <TableCell className='font-mono text-xs font-semibold text-foreground py-3 pl-5'>
                          {run.id.slice(0, 8)}...
                        </TableCell>
                        <TableCell className='text-xs text-muted-foreground whitespace-nowrap py-3'>
                          <div className='flex items-center gap-1.5'>
                            <Clock className='size-3 text-muted-foreground' />
                            {new Date(run.started_at).toLocaleString('pt-BR')}
                          </div>
                        </TableCell>
                        <TableCell className='py-3'>{getStageBadge(run.stage)}</TableCell>
                        <TableCell className='py-3'>{getStatusBadge(run.status)}</TableCell>
                        <TableCell className='text-xs text-muted-foreground font-mono whitespace-nowrap py-3'>
                          {run.duration_seconds
                            ? `${run.duration_seconds.toFixed(1)}s`
                            : run.status === 'running'
                            ? 'em andamento'
                            : '-'}
                        </TableCell>
                        <TableCell className='text-xs py-3 pr-5'>
                          {run.error_message ? (
                            <Button
                              variant='outline'
                              size='sm'
                              onClick={() => handleOpenDiagnostic(run)}
                              className='h-7 px-2.5 text-xs font-semibold gap-1.5 border-rose-300 dark:border-rose-800 bg-rose-50 text-rose-800 dark:bg-rose-950 dark:text-rose-200 hover:bg-rose-100 hover:text-rose-900 transition-colors'
                            >
                              <AlertCircle className='size-3 text-rose-600 dark:text-rose-400 shrink-0' />
                              Ver Detalhes do Erro
                            </Button>
                          ) : run.run_metadata && run.run_metadata.script_hook ? (
                            <div className='flex items-center gap-2 max-w-[400px]'>
                              <span className='text-[11px] text-muted-foreground truncate italic' title={run.run_metadata.script_hook}>
                                Hook: "{run.run_metadata.script_hook}"
                              </span>
                              <Button
                                variant='ghost'
                                size='sm'
                                onClick={() => handleOpenDiagnostic(run)}
                                className='h-6 px-1.5 text-[11px] text-muted-foreground hover:text-foreground shrink-0'
                              >
                                Ver
                              </Button>
                            </div>
                          ) : (
                            <span className='inline-flex items-center gap-1.5 text-[11px] text-muted-foreground'>
                              <CheckCircle2 className='size-3.5 text-emerald-600 dark:text-emerald-500' />
                              Executado sem erros
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

      {/* Diagnostic Details Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className='max-w-2xl border-border bg-card'>
          <DialogHeader className='border-b border-border/60 pb-3'>
            <div className='flex items-center gap-2.5'>
              <div
                className={`p-1.5 rounded-md ${
                  selectedRun?.status === 'failed'
                    ? 'bg-rose-700 text-white'
                    : 'bg-emerald-700 text-white'
                }`}
              >
                {selectedRun?.status === 'failed' ? (
                  <AlertCircle className='size-4' />
                ) : (
                  <CheckCircle2 className='size-4' />
                )}
              </div>
              <div>
                <DialogTitle className='text-base font-bold text-foreground'>
                  {selectedRun?.status === 'failed'
                    ? 'Diagnóstico de Falha da Tarefa'
                    : 'Detalhes da Execução'}
                </DialogTitle>
                <DialogDescription className='text-xs mt-0.5'>
                  Tarefa <span className='font-mono font-semibold'>{selectedRun?.id}</span> • Estágio: <span className='capitalize font-medium'>{selectedRun?.stage}</span>
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {selectedRun && (
            <div className='space-y-4 py-2 text-xs'>
              {/* Metric summary boxes */}
              <div className='grid grid-cols-3 gap-3'>
                <div className='rounded-lg border border-border/70 bg-muted/30 p-2.5'>
                  <p className='text-[10px] uppercase font-bold text-muted-foreground'>Status</p>
                  <div className='mt-1'>{getStatusBadge(selectedRun.status)}</div>
                </div>
                <div className='rounded-lg border border-border/70 bg-muted/30 p-2.5'>
                  <p className='text-[10px] uppercase font-bold text-muted-foreground'>Início</p>
                  <p className='mt-1 font-semibold text-foreground truncate'>
                    {new Date(selectedRun.started_at).toLocaleString('pt-BR')}
                  </p>
                </div>
                <div className='rounded-lg border border-border/70 bg-muted/30 p-2.5'>
                  <p className='text-[10px] uppercase font-bold text-muted-foreground'>Duração</p>
                  <p className='mt-1 font-mono font-semibold text-foreground'>
                    {selectedRun.duration_seconds
                      ? `${selectedRun.duration_seconds.toFixed(2)}s`
                      : '-'}
                  </p>
                </div>
              </div>

              {/* Error Details */}
              {selectedRun.error_message && (
                <div className='space-y-1.5'>
                  <div className='flex items-center justify-between'>
                    <span className='font-bold text-foreground text-xs flex items-center gap-1.5'>
                      <Terminal className='size-3.5 text-rose-600 dark:text-rose-400' />
                      Mensagem de Erro / Stack Trace
                    </span>
                    <Button
                      variant='ghost'
                      size='sm'
                      onClick={() => handleCopy(selectedRun.error_message)}
                      className='h-6 text-[11px] gap-1 px-2 text-muted-foreground hover:text-foreground'
                    >
                      {copied ? (
                        <Check className='size-3 text-emerald-600' />
                      ) : (
                        <Copy className='size-3' />
                      )}
                      {copied ? 'Copiado' : 'Copiar'}
                    </Button>
                  </div>
                  <div className='rounded-lg border border-rose-300 dark:border-rose-900/60 bg-slate-950 dark:bg-black p-3.5 font-mono text-[11px] leading-relaxed text-rose-300 overflow-x-auto whitespace-pre-wrap max-h-64 selection:bg-rose-900 selection:text-white'>
                    {selectedRun.error_message}
                  </div>
                </div>
              )}

              {/* Metadata Details (if present) */}
              {selectedRun.run_metadata && Object.keys(selectedRun.run_metadata).length > 0 && (
                <div className='space-y-1.5'>
                  <span className='font-bold text-foreground text-xs flex items-center gap-1.5'>
                    <FileCode className='size-3.5 text-muted-foreground' />
                    Metadados da Execução
                  </span>
                  <div className='rounded-lg border border-border bg-muted/30 p-3 font-mono text-[11px] leading-relaxed text-foreground overflow-x-auto whitespace-pre-wrap max-h-48'>
                    {JSON.stringify(selectedRun.run_metadata, null, 2)}
                  </div>
                </div>
              )}
            </div>
          )}

          <DialogFooter className='border-t border-border/60 pt-3'>
            <Button
              variant='outline'
              size='sm'
              onClick={() => setDialogOpen(false)}
              className='text-xs h-8 font-medium'
            >
              Fechar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
