import { useState } from 'react'
import { RefreshCw, Play, Database, Server, CheckCircle2, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'
import { Header } from '@/components/layout/header'
import { ThemeSwitch } from '@/components/theme-switch'
import { Button } from '@/components/ui/button'
import { triggerPipeline, HealthResponse } from '@/services/api'

interface ViralHeaderProps {
  title?: string
  subtitle?: string
  health: HealthResponse | null
  isLoading?: boolean
  onRefresh?: () => void
}

export function ViralHeader({
  title = 'ViralPanel',
  subtitle,
  health,
  isLoading = false,
  onRefresh,
}: ViralHeaderProps) {
  const [triggering, setTriggering] = useState(false)

  const handleTrigger = async () => {
    try {
      setTriggering(true)
      const res = await triggerPipeline()
      toast.success('Esteira Disparada!', {
        description: `${res.message} (Task: ${res.task_id})`,
      })
      if (onRefresh) onRefresh()
    } catch (err: any) {
      toast.error('Erro ao disparar esteira', {
        description: err.response?.data?.detail || err.message,
      })
    } finally {
      setTriggering(false)
    }
  }

  const isHealthy = health?.status === 'healthy'
  const isDbOk = health?.database === 'connected'
  const isRedisOk = health?.redis === 'connected'

  return (
    <Header fixed className='border-b border-border/80 bg-background/95 backdrop-blur-md'>
      <div className='flex flex-1 items-center justify-between gap-4'>
        {/* Title / Subtitle */}
        <div className='flex flex-col'>
          <h1 className='text-lg font-bold tracking-tight text-foreground sm:text-xl'>
            {title}
          </h1>
          {subtitle && (
            <p className='hidden text-xs text-muted-foreground sm:block'>
              {subtitle}
            </p>
          )}
        </div>

        {/* Right Actions & Status */}
        <div className='flex items-center gap-2.5 sm:gap-3'>
          {/* Health Status Pills - Solid, No Neon */}
          <div className='hidden items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-xs md:flex shadow-xs'>
            <div className='flex items-center gap-1.5'>
              <Database className='size-3.5 text-muted-foreground' />
              <span className='font-medium text-muted-foreground'>DB:</span>
              <span
                className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold text-white tracking-wide ${
                  isDbOk
                    ? 'bg-emerald-700 dark:bg-emerald-800'
                    : 'bg-rose-700 dark:bg-rose-800'
                }`}
              >
                {isDbOk ? 'CONECTADO' : 'OFFLINE'}
              </span>
            </div>

            <div className='h-3.5 w-px bg-border' />

            <div className='flex items-center gap-1.5'>
              <Server className='size-3.5 text-muted-foreground' />
              <span className='font-medium text-muted-foreground'>Redis:</span>
              <span
                className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold text-white tracking-wide ${
                  isRedisOk
                    ? 'bg-emerald-700 dark:bg-emerald-800'
                    : 'bg-rose-700 dark:bg-rose-800'
                }`}
              >
                {isRedisOk ? 'CONECTADO' : 'OFFLINE'}
              </span>
            </div>
          </div>

          {/* Simple status badge for small screens */}
          <div className='flex md:hidden'>
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold text-white ${
                isHealthy
                  ? 'bg-emerald-700 dark:bg-emerald-800'
                  : 'bg-rose-700 dark:bg-rose-800'
              }`}
            >
              {isHealthy ? (
                <CheckCircle2 className='size-3' />
              ) : (
                <AlertCircle className='size-3' />
              )}
              {health?.status || 'verificando...'}
            </span>
          </div>

          {/* Refresh Button */}
          {onRefresh && (
            <Button
              variant='outline'
              size='sm'
              onClick={onRefresh}
              disabled={isLoading}
              className='gap-1.5 h-8 border-border shadow-xs hover:bg-accent'
              title='Recarregar dados'
            >
              <RefreshCw className={`size-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span className='hidden sm:inline text-xs font-medium'>Atualizar</span>
            </Button>
          )}

          {/* Trigger Daily Pipeline Button - Solid Primary */}
          <Button
            size='sm'
            onClick={handleTrigger}
            disabled={triggering}
            className='gap-1.5 h-8 font-medium bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white shadow-xs'
          >
            <Play className={`size-3.5 fill-current ${triggering ? 'animate-pulse' : ''}`} />
            <span className='hidden sm:inline text-xs'>Disparar Esteira</span>
            <span className='sm:hidden text-xs'>Disparar</span>
          </Button>

          {/* Dark / Light Mode Switch */}
          <div className='border-l border-border pl-1 sm:pl-2'>
            <ThemeSwitch />
          </div>
        </div>
      </div>
    </Header>
  )
}
