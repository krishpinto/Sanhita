// Dismissible demo banner — synthetic patients only.

import { useState } from 'react';

import { Banner } from './ui';

export function DemoWatermark() {
  const [visible, setVisible] = useState(true);
  if (!visible) return null;
  return <Banner onDismiss={() => setVisible(false)} />;
}
