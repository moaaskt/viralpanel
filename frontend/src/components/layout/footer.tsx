import { cn } from '@/lib/utils'

type FooterProps = React.ComponentProps<'footer'>

export function Footer({ className, ...props }: FooterProps) {
  return (
    <footer
      className={cn(
        'text-muted-foreground mt-auto shrink-0 border-t px-4 py-4 text-center text-xs',
        className
      )}
      {...props}
    >
      <span>&copy; {new Date().getFullYear()} ViralPanel • Pipeline Autônomo de Conteúdo Viral (Gemini 2.5 Flash + XTTS v2 + Celery)</span>
    </footer>
  )
}
