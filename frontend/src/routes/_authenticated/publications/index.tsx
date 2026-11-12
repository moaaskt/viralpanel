import { createFileRoute } from '@tanstack/react-router'
import { PublicationsPage } from '@/features/publications'

export const Route = createFileRoute('/_authenticated/publications/')({
  component: PublicationsPage,
})

