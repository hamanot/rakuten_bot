import json
import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


class ItemAnalysisLogic:
    def __init__(self, debug_mode=True):
        self.driver = None
        self.debug_mode = debug_mode

    def _init_driver(self):
        if self.driver is None:
            options = Options()
            if not self.debug_mode:
                options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--log-level=3')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            chrome_path = os.path.join(project_root, "bin", "chromedriver.exe")

            try:
                self.driver = webdriver.Chrome(executable_path=chrome_path, options=options)
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception as e:
                raise Exception("ChromeDriver起動失敗: {}".format(e))

    def fetch_item_variants(self, url):
        self._init_driver()
        self.driver.get(url)

        # ターゲット要素が現れるまで待機
        try:
            wait = WebDriverWait(self.driver, 10)
            # SKUボタンか、もしくは了承事項のセレクトボックスが出るまで待つ
            wait.until(lambda d: d.execute_script(
                "return document.querySelector('.type-sku-button--1i7g2') || document.querySelector('.select--3Nrso');"
            ))
        except:
            pass

        script = """
        var res = { groups: [], skuMap: {}, common: {}, debug: {} };
        try {
            // 1. ID取得
            var targetEl = document.querySelector('[data-item-data]') || 
                           document.querySelector('[data-item-to-compare-data]');
            if (targetEl) {
                var raw = targetEl.getAttribute('data-item-data') || targetEl.getAttribute('data-item-to-compare-data');
                var d = JSON.parse(raw);
                d = Array.isArray(d) ? d[0] : d;
                res.common.itemid = (d.itemId || "").toString();
                res.common.shopid = (d.shopId || "").toString();
            }

            // SKUベースID取得
            var m = document.body.innerHTML.match(/compass_sku_(\\d+)_/);
            var base = m ? m[0] : "";
            res.common.base_variant_id = base;

            var gIdx = 0;

            // 2. SKUボタン群 (熨斗、セット数など)
            document.querySelectorAll('.padding-bottom-small--Ql3Ez').forEach(function(container) {
                var btns = Array.from(container.querySelectorAll('.type-sku-button--1i7g2'));
                if (btns.length > 0) {
                    var label = container.querySelector('.layout-inline--QSCjX span')?.innerText.trim() || "項目" + (gIdx + 1);
                    res.groups.push({
                        id: gIdx++,
                        name: label.replace(/[：:]/g, ''),
                        options: btns.map(b => b.innerText.trim()),
                        type: 'sku'
                    });
                }
            });

            // 3. 了承事項 (select--3Nrso)
            // あなたが提示した select タグの構造をホワイトリストで狙い撃ち
            document.querySelectorAll('.container--3ZLr9').forEach(function(container) {
                var selectEl = container.querySelector('select.select--3Nrso');
                if (selectEl) {
                    var label = container.querySelector('.text-container--3DrET')?.innerText.trim() || "確認事項";
                    // optionからテキストを取得
                    var opts = Array.from(selectEl.options).map(o => o.text.trim());

                    res.groups.push({
                        id: gIdx++,
                        name: label,
                        options: opts,
                        type: 'choice'
                    });
                }
            });

            // 4. SKUマップ生成 (type: 'sku' のものだけで組み合わせる)
            var skuGroups = res.groups.filter(g => g.type === 'sku');
            if (skuGroups.length > 0 && base) {
                function combine(list, n, result, current) {
                    if (n === list.length) { result.push(current.join(',')); return; }
                    for (var j = 0; j < list[n].options.length; j++) {
                        combine(list, n + 1, result, current.concat([list[n].options[j]]));
                    }
                }
                var combs = [];
                combine(skuGroups, 0, combs, []);
                combs.forEach((c, i) => { res.skuMap[c] = base + (i + 1); });
            }

        } catch (e) { res.debug.js_crash = e.message; }
        return res;
        """
        data = self.driver.execute_script(script)

        # デバッグログを強化
        if self.debug_mode:
            print("\n" + "=" * 50)
            print(" [ANALYSIS DEBUG LOG]")
            print(f" SHOP_ID : {data['common'].get('shopid')}")
            print(f" ITEM_ID : {data['common'].get('itemid')}")
            print(f" BASE_ID : {data['common'].get('base_variant_id')}")
            print(f" GROUPS  : {len(data['groups'])} 項目検出")

            for g in data['groups']:
                g_type = "[SKU]" if g.get('type') == 'sku' else "[CHOICE]"
                print(f"  {g_type} {g['name']}")
                print(f"    options: {g['options']}")

            if data.get('debug', {}).get('js_crash'):
                print(f" JS_ERROR: {data['debug']['js_crash']}")
            print("=" * 50 + "\n")
            sys.stdout.flush()

        if not data['common'].get('itemid') or not data['common'].get('shopid'):
            raise Exception("抽出失敗: IDを取得できませんでした。")

        return data

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None