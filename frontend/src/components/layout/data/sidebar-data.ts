import {
  LayoutDashboard,
  Activity,
  Film,
  Share2,
  Palette,
  Zap,
} from 'lucide-react'
import { type SidebarData } from '../types'

export const sidebarData: SidebarData = {
  user: {
    name: 'Criador Solo',
    email: 'admin@viralpanel.local',
    avatar: '',
  },
  teams: [
    {
      name: 'ViralPanel',
      logo: Zap,
      plan: 'Pipeline Autônomo',
    },
  ],
  navGroups: [
    {
      title: 'Pipeline & Conteúdo',
      items: [
        {
          title: 'Visão Geral',
          url: '/',
          icon: LayoutDashboard,
        },
        {
          title: 'Esteira de Produção',
          url: '/pipeline',
          icon: Activity,
        },
        {
          title: 'Mineração & Roteiros',
          url: '/videos',
          icon: Film,
        },
        {
          title: 'Publicações Oficiais',
          url: '/publications',
          icon: Share2,
        },
      ],
    },
    {
      title: 'Sistema',
      items: [
        {
          title: 'Aparência & Tema',
          url: '/settings/appearance',
          icon: Palette,
        },
      ],
    },
  ],
}
