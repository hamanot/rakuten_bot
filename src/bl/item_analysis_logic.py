import json
import os
import sys
import time
import re
from selenium.webdriver.support.ui import WebDriverWait
from component.chrome_driver_manager import ChromeDriverManager


class ItemAnalysisLogic:
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode

    def fetch_item_variants(self, url):
        driver = ChromeDriverManager.get_driver()
        driver.get(url)

        try:
            wait = WebDriverWait(driver, 10)
            wait.until(lambda d: d.execute_script(
                "return document.querySelector('.type-sku-button--1i7g2, .select--3Nrso, span.normal_reserve_item_name, h2, h1');"
            ))
        except:
            pass

        # --- JavaScript 解析ロジック (解析・ログ出力ともに完全維持) ---
        script = """
        var res = { groups: [], skuMap: {}, common: {}, debug: { log: [] } };
        function addLog(msg) { res.debug.log.push(msg); }

        try {
            var titleEl = document.querySelector('span.normal_reserve_item_name, h2.item_name, h1, h2');
            res.common.title = titleEl ? titleEl.innerText.trim() : document.title;

            var targetEl = document.querySelector('[data-item-data], [data-item-to-compare-data]');
            if (targetEl) {
                var raw = targetEl.getAttribute('data-item-data') || targetEl.getAttribute('data-item-to-compare-data');
                var d = JSON.parse(raw); d = Array.isArray(d) ? d[0] : d;
                res.common.itemid = (d.itemId || "").toString();
                res.common.shopid = (d.shopId || "").toString();
            }

            // 【核心】変な数字の出処をログに残す
            var htmlSnippet = document.body.innerHTML;
            var m = htmlSnippet.match(/compass_sku_(\\d+)_/);
            var skuPrefix = "";

            if (m) {
                addLog("Match Found in HTML: " + m[0]);
                skuPrefix = m[0];
            } else {
                addLog("No 'compass_sku_' found. Fallback to 13-digit search.");
                var mDigit = htmlSnippet.match(/\\d{13}/);
                if (mDigit) {
                    addLog("Found 13-digit string: " + mDigit[0]);
                    skuPrefix = mDigit[0];
                }
            }
            res.common.base_variant_id = skuPrefix;

            var gIdx = 0;
            document.querySelectorAll('.padding-bottom-small--Ql3Ez').forEach(function(container) {
                var btns = Array.from(container.querySelectorAll('.type-sku-button--1i7g2'));
                if (btns.length > 0) {
                    var label = container.querySelector('.layout-inline--QSCjX span')?.innerText.trim() || "項目" + (gIdx + 1);
                    res.groups.push({ id: gIdx++, name: label.replace(/[：:]/g, ''), options: btns.map(b => b.innerText.trim()), type: 'sku' });
                }
            });

            document.querySelectorAll('.container--3ZLr9').forEach(function(container) {
                var selectEl = container.querySelector('select.select--3Nrso');
                if (selectEl) {
                    var label = container.querySelector('.text-container--3DrET')?.innerText.trim() || "確認事項";
                    var opts = Array.from(selectEl.options).filter(o => o.value !== "").map(o => o.text.trim());
                    res.groups.push({ id: gIdx++, name: label, options: opts, type: 'choice' });
                }
            });

            var skuGroups = res.groups.filter(g => g.type === 'sku');
            if (skuGroups.length > 0 && skuPrefix !== "") {
                function combine(list, n, result, current) {
                    if (n === list.length) { result.push(current.join(',')); return; }
                    for (var j = 0; j < list[n].options.length; j++) { combine(list, n + 1, result, current.concat([list[n].options[j]])); }
                }
                var combs = [];
                combine(skuGroups, 0, combs, []);
                combs.forEach((c, i) => { res.skuMap[c] = skuPrefix + (i + 1); });
                res.common.vid = res.skuMap[combs[0]];
                addLog("Final VID Example: " + res.common.vid);
            }
        } catch (e) { res.debug.js_crash = e.message; }
        return res;
        """
        data = driver.execute_script(script)

        if self.debug_mode:
            self._print_detailed_log(data)

        return data

    def _print_detailed_log(self, data):
        print("\n" + "!" * 60)
        print(" [DETAILED EXTRACTION LOG]")
        for log in data.get('debug', {}).get('log', []):
            print(f" > {log}")
        print(f" BASE_PREFIX : '{data['common'].get('base_variant_id')}'")
        print(f" FINAL_VID   : '{data['common'].get('vid')}'")
        print("!" * 60 + "\n")
        sys.stdout.flush()

    def generate_post_payload(self, saved_action_data):
        parts = saved_action_data.split('|')
        payload = {
            "itemid": parts[-2], "shopid": parts[-1], "units": "1", "device": "pc",
            "userid": "itempage", "response_encode": "utf8", "choice[]": [p for p in parts if ":" in p]
        }
        if parts[0].startswith('compass_sku_'):
            payload["variant_id"] = parts[0]
        return payload

    def close(self):
        # 【修正】シングルトンから「今あるインスタンス」だけをチェックして閉じる
        try:
            if hasattr(ChromeDriverManager, '_driver') and ChromeDriverManager._driver:
                ChromeDriverManager._driver.quit()
                ChromeDriverManager._driver = None
        except:
            pass