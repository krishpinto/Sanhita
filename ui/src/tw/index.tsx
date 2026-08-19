// CSS-enabled wrappers around the RN primitives this app actually uses.
// react-native-css requires explicit `useCssElement` wrapping — screens and
// components import View/Text/etc. from here, not from 'react-native'.

import { useCssElement, useNativeVariable as useFunctionalVariable } from 'react-native-css';

import type React from 'react';
import {
  Pressable as RNPressable,
  ScrollView as RNScrollView,
  Text as RNText,
  TextInput as RNTextInput,
  View as RNView,
} from 'react-native';

export const useCSSVariable =
  process.env.EXPO_OS !== 'web' ? useFunctionalVariable : (variable: string) => `var(${variable})`;

// Explicit <typeof RNX> type arguments below short-circuit TS2590 ("union
// type too complex") — RN's component prop types (ScrollView/View especially)
// are complex enough that leaving the generic to be inferred blows past TS's
// instantiation limit once intersected with our own className props.

export type ViewProps = React.ComponentPropsWithRef<typeof RNView> & { className?: string };
export const View = (props: ViewProps): React.ReactElement =>
  useCssElement<typeof RNView>(RNView, props, { className: 'style' });
View.displayName = 'CSS(View)';

export type TextProps = React.ComponentPropsWithRef<typeof RNText> & { className?: string };
export const Text = (props: TextProps): React.ReactElement =>
  useCssElement<typeof RNText>(RNText, props, { className: 'style' });
Text.displayName = 'CSS(Text)';

export type ScrollViewProps = React.ComponentPropsWithRef<typeof RNScrollView> & {
  className?: string;
  contentContainerClassName?: string;
};
export const ScrollView = (props: ScrollViewProps): React.ReactElement =>
  // ScrollView's/Pressable's prop types (function-union `style`, many
  // platform-conditional variants) push react-native-css's mapping generic
  // past TS's instantiation limit (TS2590) even with an explicit type
  // argument. The exported ScrollViewProps/ReactElement types above are what
  // consumers see and remain fully checked; only this internal call is
  // loosely typed.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useCssElement(RNScrollView as any, props, {
    className: 'style',
    contentContainerClassName: 'contentContainerStyle',
  });
ScrollView.displayName = 'CSS(ScrollView)';

export type PressableProps = React.ComponentPropsWithRef<typeof RNPressable> & { className?: string };
export const Pressable = (props: PressableProps): React.ReactElement =>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useCssElement(RNPressable as any, props, { className: 'style' });
Pressable.displayName = 'CSS(Pressable)';

export type TextInputProps = React.ComponentPropsWithRef<typeof RNTextInput> & { className?: string };
export const TextInput = (props: TextInputProps): React.ReactElement =>
  useCssElement<typeof RNTextInput>(RNTextInput, props, { className: 'style' });
TextInput.displayName = 'CSS(TextInput)';
