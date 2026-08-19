import { useWindowDimensions } from 'react-native';

export const DESKTOP_BREAKPOINT = 768;

export function useBreakpoint() {
  const { width } = useWindowDimensions();
  const isDesktop = width >= DESKTOP_BREAKPOINT;
  return { width, isDesktop, isMobile: !isDesktop };
}
