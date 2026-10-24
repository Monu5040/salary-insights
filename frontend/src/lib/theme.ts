import type { ConfigProviderProps, ThemeConfig } from "antd";

/**
 * The app's look (design §8): Inter, an indigo accent, and white cards on a cool grey page.
 * Every text colour meets WCAG AA contrast of 4.5:1, which Ant Design's defaults don't: its
 * blue is 4.1:1 against white, its danger red 3.3:1, grey secondary text 3.3:1, and the green,
 * gold and orange tags 3.4, 2.8 and 3.4:1. The end-to-end tests check pages with axe.
 */
export const theme: ThemeConfig = {
  token: {
    // Self-hosted (package @fontsource-variable/inter), as the CSP allows fonts from 'self' only.
    fontFamily:
      "'Inter Variable', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    // Indigo 600 for links, buttons and the selected item: 6.3:1 with white, 5.9:1 on the grey.
    colorPrimary: "#4f46e5",
    colorInfo: "#4f46e5",
    colorLink: "#4f46e5",
    // Hovered and pressed go darker, not lighter, so white text on them keeps its contrast.
    colorPrimaryHover: "#4338ca",
    colorPrimaryActive: "#3730a3",
    colorLinkHover: "#4338ca",
    colorLinkActive: "#3730a3",
    // Red 7 for danger buttons and error messages: 5.6:1 on white.
    colorError: "#cf1322",
    // Text in a dark slate rather than black: 12.7:1 on white, secondary text 5.6:1.
    colorTextBase: "#0f172a",
    // Hints and placeholders: 5.0:1 on white, 4.9:1 on the page's grey.
    colorTextTertiary: "rgba(15, 23, 42, 0.62)",
    colorTextPlaceholder: "rgba(15, 23, 42, 0.62)",
    colorBgLayout: "#f5f7fb",
    colorBorderSecondary: "#e9edf3",
    borderRadius: 8,
    borderRadiusLG: 12,
    controlHeight: 36,
    // Tag text, on each tag's pale background: green 8 (5.4:1), gold 9 (6.7:1), orange 8 (5.1:1).
    green7: "#237804",
    gold7: "#874d00",
    orange7: "#ad4e00",
  },
  components: {
    // The sidebar's menu, on its dark indigo: items 9.2:1, the selected one 12:1.
    Menu: {
      darkItemBg: "transparent",
      darkItemColor: "rgba(226, 232, 240, 0.8)",
      darkItemHoverColor: "#ffffff",
      darkItemHoverBg: "rgba(255, 255, 255, 0.06)",
      darkItemSelectedBg: "rgba(99, 102, 241, 0.28)",
      darkItemSelectedColor: "#ffffff",
      itemBorderRadius: 8,
      itemHeight: 40,
      itemMarginInline: 12,
      iconSize: 16,
    },
    Card: { headerFontSize: 16 },
    // Column names 5.5:1 on the header's tint.
    Table: {
      headerBg: "#f8fafc",
      headerColor: "rgba(15, 23, 42, 0.65)",
      headerSplitColor: "transparent",
      rowHoverBg: "#f7f8fe",
    },
    Statistic: { titleFontSize: 13, contentFontSize: 28 },
  },
};

/** Cards lift a little off the page. */
export const card: ConfigProviderProps["card"] = {
  style: { boxShadow: "0 1px 2px rgba(16, 24, 40, 0.05), 0 1px 3px rgba(16, 24, 40, 0.04)" },
};
