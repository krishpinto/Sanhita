// Review View — the whole protocol tree at once, like a printed flowchart,
// for a senior clinician to sign off on a protocol before it ships. Not
// built yet: it's item 3 in CLAUDE.md's locked build order, right after the
// Field View (item 2, built) proves the engine out. Until then,
// ../../protocol-tree-demo.html is the stand-in — hand-built from the same
// fever-adult content and already walkable in a browser.

import { T } from '@/components/ui';
import { View } from '@/tw';

export default function ReviewScreen() {
  return (
    <View className="flex-1 bg-bg items-center justify-center p-6 gap-2">
      <T variant="title" className="text-center">
        Review view — not built yet
      </T>
      <T variant="secondary" tone="secondary" className="text-center">
        Next up per CLAUDE.md&apos;s build order. Until then, see
        protocol-tree-demo.html for the same content as a whole-tree view.
      </T>
    </View>
  );
}
