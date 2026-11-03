import { defineConfig } from "@apps-in-toss/web-framework/config";

export default defineConfig({
  // 앱인토스 콘솔에 등록한 appName과 반드시 같아야 업로드할 수 있어요. (등록 후 변경 불가)
  appName: "harusangsik",
  brand: {
    primaryColor: "#2F6BFF"
  },
  navigationBar: {
    withBackButton: true,
    withHomeButton: false,
    withTitle: true
  },
  webView: {
    bounces: false,
    pullToRefreshEnabled: false,
    overScrollMode: "never"
  },
  permissions: [],
  webBundleDir: "dist"
});
