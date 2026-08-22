# IDAC 県別データ中継（CORS回避）

公式 `initiald.sega.jp` のランキングAPIはブラウザから直接読めません（CORS非対応）。  
このリポジトリは **GitHub Actions で県別・全国データを取得**し、`enrich.json` を **GitHub Pages で公開**します。

GitHub Pages は `Access-Control-Allow-Origin: *` 相当で読めるため、ローカルHTMLからも `fetch` 可能です。

## 公開されるデータ

| フィールド | 内容 |
|-----------|------|
| `pridePoint` / `prideId` | PRIDE数値・バッジ（0〜99含む） |
| `starCnt` | ランクの星の数 |
| `onlineBattleRankId` | Ruby / Sapphire / Emerald 画像ID |
| `updateDate` など | 店舗・車種・RP |

アクティブ勢（参考トラッカー掲載者）を中心に、全国TOP1000外は **県別ランキングから補完**します。

## セットアップ（初回）

1. GitHub で **新しい公開リポジトリ**を作成（例: `idac-enrich-relay`）
2. このフォルダの内容を push
   - `fetch_enrich.py`
   - `.github/workflows/update-enrich.yml`
3. リポジトリ **Settings → Pages → Build and deployment**
   - Source: **GitHub Actions**
4. **Actions** タブで `Update IDAC enrich.json` を **Run workflow**
5. 数分後、次のURLでJSONが配信されます

```
https://<user>.github.io/<repo>/enrich.json
```

## ローカルで試す

```bash
python3 fetch_enrich.py
# → enrich.json が生成される
```

## ビューアHTML側の設定

`idac-live-*.html` 内の定数を、自分の Pages URL に合わせてください。

```js
const RELAY_URL = "https://<user>.github.io/<repo>/enrich.json";
```

未設定や取得失敗時は、埋め込みデータ・参考トラッカーのみで動作します。

## 更新頻度

- GitHub Actions: 約5分ごと（`cron: "*/5 * * * *"`）
- GitHub の schedule は遅延することがあります
- 手動: Actions → Run workflow

## 注意

- 非公式の中継です。SEGA公式ではありません
- 負荷軽減のため、主にトラッカー上のアクティブ勢を対象にしています
- 利用は自己責任でお願いします
