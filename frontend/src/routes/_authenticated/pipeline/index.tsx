import { createFileRoute } from '@tanstack/react-router'
import { PipelinePage } from '@/features/pipeline'

export const Route = createFileRoute('/_authenticated/pipeline/')({
  component: PipelinePage,
})

