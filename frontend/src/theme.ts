import { extendTheme, type ThemeConfig } from '@chakra-ui/react';

// Diretriz estrita: Visual corporativo, sóbrio e elegante. SEM cores neon ou fluorescentes.
const config: ThemeConfig = {
  initialColorMode: 'light',
  useSystemColorMode: false,
};

export const theme = extendTheme({
  config,
  fonts: {
    heading: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    body: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  },
  colors: {
    brand: {
      50: '#F0F7FF',
      100: '#E0EFFF',
      200: '#BAE0FF',
      300: '#7CC4FA',
      400: '#38A3F5',
      500: '#1D6FD8', // Azul corporativo refinado
      600: '#1454AB',
      700: '#114187',
      800: '#0E346A',
      900: '#0B2852',
    },
    slate: {
      50: '#F8FAFC',
      100: '#F1F5F9',
      200: '#E2E8F0',
      300: '#CBD5E1',
      400: '#94A3B8',
      500: '#64748B',
      600: '#475569',
      700: '#334155',
      800: '#1E293B',
      900: '#0F172A',
    },
  },
  styles: {
    global: {
      body: {
        bg: '#F8FAFC',
        color: '#1E293B',
      },
    },
  },
  components: {
    Button: {
      baseStyle: {
        fontWeight: '500',
        borderRadius: 'md',
      },
      variants: {
        solid: {
          bg: 'brand.500',
          color: 'white',
          _hover: {
            bg: 'brand.600',
          },
        },
      },
    },
    Card: {
      baseStyle: {
        container: {
          borderWidth: '1px',
          borderColor: 'slate.200',
          borderRadius: 'lg',
          boxShadow: 'sm',
          bg: 'white',
        },
      },
    },
  },
});

