diff --git a/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/d3.exports.js b/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/d3.exports.js
new file mode 100644
index 0000000000000000000000000000000000000000..54a3b307a017bbb1c71ae0abc897a442a7d40efc
--- /dev/null
+++ b/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/d3.exports.js
@@ -0,0 +1,6 @@
+// SPDX-License-Identifier: Apache-2.0
+const d3 = window.d3;
+if (!d3) {
+  throw new Error('d3 global not found');
+}
+export default d3;
