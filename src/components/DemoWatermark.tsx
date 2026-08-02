// Slim amber ribbon making it unmistakable that no real patient data is
// involved. Restyled per the design system — legible, not screaming. Stays
// until real-patient compliance work exists; never remove.

import { TriangleAlert } from 'lucide-react-native';

import { T } from './ui';
import { View } from '@/tw';

export function DemoWatermark() {
  return (
    <View className="flex-row items-center justify-center gap-2 bg-ribbon-bg py-1 px-3">
      <TriangleAlert size={12} color="#B7791F" strokeWidth={2.2} />
      <T variant="caption" className="font-semibold tracking-wide" style={{ color: '#B7791F' }}>
        Demo — synthetic patients only · not for clinical use
      </T>
    </View>
  );
}
