// Review View — placeholder until built. Restyled shell only.

import { AppShell, PageContainer } from '@/components/layout';
import { T } from '@/components/ui';
import { View } from '@/tw';

export default function ReviewScreen() {
  return (
    <AppShell>
      <View className="flex-1 bg-bg items-center justify-center">
        <PageContainer className="items-center gap-2 py-12">
          <T variant="pageTitle" className="text-center">
            Review view — not built yet
          </T>
          <T variant="secondary" tone="secondary" className="text-center">
            Next up per the build order. Until then, see protocol-tree-demo.html for the same content as a whole-tree
            view.
          </T>
        </PageContainer>
      </View>
    </AppShell>
  );
}
